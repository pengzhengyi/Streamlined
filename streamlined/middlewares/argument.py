from dataclasses import replace
from functools import partial
from typing import Any, Dict, Iterable

from ..common import DEFAULT_KEYERROR, IS_NOT_DICT, VALUE
from ..services import Scoped
from .action import Action
from .cleanup import Cleanup
from .log import Log
from .middleware import APPLY_INTO, APPLY_ONTO, Context, Middleware, WithMiddlewares
from .middlewares import StackedMiddlewares
from .name import NAME, Name
from .validator import Validator


def _MISSING_ARGUMENT_NAME(value: Dict[str, Any]) -> bool:
    return NAME not in value


def _MISSING_ARGUMENT_VALUE(value: Dict[str, Any]) -> bool:
    return VALUE not in value


class Argument(Middleware, WithMiddlewares):
    def _init_middleware_types(self) -> None:
        super()._init_middleware_types()
        self.middleware_types.extend([Name, Validator, Action, Log, Cleanup])

    def _init_middleware_apply_methods(self) -> None:
        super()._init_middleware_apply_methods()
        self.middleware_apply_methods.extend(
            [APPLY_ONTO, APPLY_ONTO, APPLY_INTO, APPLY_ONTO, APPLY_ONTO]
        )

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

    def _do_parse(self, value: Any) -> Dict[str, Any]:
        self.verify(value)
        return {"middlewares": list(self.create_middlewares_from(value))}

    async def _set_value(self, scoped: Scoped) -> Scoped:
        name = scoped.getmagic("name")
        value = scoped.getmagic("value")
        scoped.set(name, value, 1)
        return scoped

    async def _do_apply(self, context: Context) -> Scoped:
        next_function = partial(self._set_value, scoped=context.scoped)
        coroutine = WithMiddlewares.apply(self, replace(context, next=next_function))
        await coroutine()

        await context.next()
        return context.scoped


ARGUMENT = Argument.get_name()


class Arguments(StackedMiddlewares):
    pass


ARGUMENTS = Arguments.get_name()
