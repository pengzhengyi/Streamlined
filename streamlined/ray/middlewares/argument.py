from dataclasses import replace
from typing import Any, Awaitable, Callable, ClassVar, Dict, Iterable, List, Type

from ..common import (
    ACTION,
    AND,
    ASYNC_VOID,
    DEFAULT,
    DEFAULT_KEYERROR,
    HANDLERS,
    IDENTITY_FACTORY,
    IS_CALLABLE,
    IS_DICT,
    IS_NONE,
    IS_NOT_CALLABLE,
    IS_NOT_DICT,
    IS_STR,
    NOOP,
    VALUE,
    get_or_raise,
)
from ..services import Scoped
from .action import Action
from .cleanup import Cleanup
from .log import LOG, Log
from .middleware import Middleware, MiddlewareContext, WithMiddlewares
from .name import NAME, Name
from .parser import Parser
from .validator import Validator


def _MISSING_ARGUMENT_NAME(value: Dict) -> bool:
    return NAME not in value


def _MISSING_ARGUMENT_VALUE(value: Dict) -> bool:
    return VALUE not in value


class Argument(Parser, Middleware, WithMiddlewares):
    def _init_middleware_types(self):
        super()._init_middleware_types()
        self.middleware_types.extend([Name, Validator, Action, Log, Cleanup])

    def create_middlewares_from(self, value: Dict[str, Any]) -> Iterable[Middleware]:
        for middleware_type, middleware_name in zip(
            self.middleware_types, self.get_middleware_names()
        ):
            if middleware_type is Action:
                new_value = {middleware_name: value[VALUE]}
                yield middleware_type(new_value)
            elif middleware_name in value:
                yield middleware_type(value)

    @classmethod
    def verify(cls, value: Any) -> None:
        super().verify(value)

        if IS_NOT_DICT(value):
            raise TypeError(f"{value} should be dict")

        if _MISSING_ARGUMENT_NAME(value):
            raise DEFAULT_KEYERROR(value, NAME)

        if _MISSING_ARGUMENT_VALUE(value):
            raise DEFAULT_KEYERROR(value, VALUE)

    def _do_parse(self, value: Any) -> Dict:
        self.verify(value)
        return {"middlewares": list(self.create_middlewares_from(value))}

    async def _do_apply(self, context: MiddlewareContext):
        action_middleware_index = self.middleware_types.index(Action)
        after_action_middlewares = self.get_middlewares_by_type(
            self.middleware_types[action_middleware_index + 1 :]
        )
        after_action_coroutine = self.apply_middlewares_to(
            context=context, middlewares=after_action_middlewares
        )

        action_context = replace(context, next=after_action_coroutine)
        action_coroutine = self.apply_middlewares(
            context=action_context, middlewares=self.get_middlewares_by_type([Action])
        )

        before_action_middlewares = self.get_middlewares_by_type(
            self.middleware_types[:action_middleware_index]
        )
        before_action_context = replace(context, next=action_coroutine)
        before_coroutine = self.apply_middlewares_to(
            context=before_action_context, middlewares=before_action_middlewares
        )

        scoped: Scoped = await before_coroutine()
        scoped.set(scoped.getmagic("name"), scoped.getmagic("value"), 1)
        return scoped


ARGUMENT = Argument.get_name()
