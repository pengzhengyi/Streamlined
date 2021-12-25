from dataclasses import replace
from typing import Any, Awaitable, Dict, Iterable, List

from ..common import DEFAULT_KEYERROR, IS_DICT, IS_LIST, IS_NONE, IS_NOT_DICT, VALUE
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


def _IS_NOT_LIST_OF_DICT(value: Any) -> bool:
    if IS_LIST(value):
        for listitem in value:
            if IS_NOT_DICT(listitem):
                return True
        return False
    else:
        return True


def _TRANSFORM_WHEN_ARGUMENTS_IS_NONE(value: None) -> List[Dict[str, Any]]:
    return []


def _TRANSFORM_WHEN_ARGUMENTS_IS_DICT(value: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [value]


class Arguments(Parser, Middleware, WithMiddlewares):
    def _init_middleware_types(self):
        super()._init_middleware_types()
        self.middleware_types.append(Argument)

    def create_middlewares_from(self, value: List[Dict[str, Any]]) -> Iterable[Middleware]:
        for middleware_type, middleware_name in zip(
            self.middleware_types, self.get_middleware_names()
        ):
            if middleware_type is Argument:
                for argument_value in value:
                    new_value = {ARGUMENT: argument_value}
                    yield middleware_type(new_value)

    def _init_simplifications(self) -> None:
        super()._init_simplifications()

        # `{ARGUMENTS: None}` -> `{ARGUMENTS: []}`
        self.simplifications.append((IS_NONE, _TRANSFORM_WHEN_ARGUMENTS_IS_NONE))

        # `{ARGUMENTS: {...}}` -> `{ARGUMENTS: [{...}]}`
        self.simplifications.append((IS_DICT, _TRANSFORM_WHEN_ARGUMENTS_IS_DICT))

    @classmethod
    def verify(cls, value: Any) -> None:
        super().verify(value)

        if _IS_NOT_LIST_OF_DICT(value):
            raise TypeError(f"{value} should be list of dict")

    def _do_parse(self, value: Any) -> Dict:
        self.verify(value)
        return {"middlewares": list(self.create_middlewares_from(value))}

    async def _do_apply(self, context: MiddlewareContext) -> Awaitable[Scoped]:
        coroutine = WithMiddlewares.apply_to(self, context)
        return await coroutine()


ARGUMENTS = Arguments.get_name()
