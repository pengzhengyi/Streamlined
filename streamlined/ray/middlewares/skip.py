from typing import Any, Callable

from ..common import (
    ACTION,
    AND,
    CONTRADICTION,
    DEFAULT_KEYERROR,
    IDENTITY_FACTORY,
    IS_CALLABLE,
    IS_DICT,
    IS_NONE,
    IS_NOT_CALLABLE,
    IS_NOT_DICT,
    NOOP,
    RETURN_FALSE,
    VALUE,
)
from .action import Action
from .middleware import Middleware, MiddlewareContext
from .parser import Parser


def _TRANSFORM_WHEN_NOT_DICT(value):
    return {VALUE: value}


def _MISSING_ACTION(value):
    return ACTION not in value


def _TRANSFORM_WHEN_MISSING_ACTION(value):
    value[ACTION] = NOOP
    return value


def _MISSING_VALUE(value):
    return VALUE not in value


def _TRANSFORM_WHEN_MISSING_VALUE(value):
    value[VALUE] = RETURN_FALSE
    return value


class Skip(Parser, Middleware):
    @classmethod
    def verify(cls, value: Any) -> None:
        super().verify(value)

        if not IS_DICT(value):
            raise TypeError(f"{value} should be dict")

        if _MISSING_ACTION(value):
            raise DEFAULT_KEYERROR(value, ACTION)

        if _MISSING_VALUE(value):
            raise DEFAULT_KEYERROR(value, VALUE)

    @property
    def _when_skip(self) -> Callable:
        return self._action

    def _init_simplifications(self) -> None:
        super()._init_simplifications()

        # `{'skip': None}` -> `{'skip': False}`
        self.simplifications.append((IS_NONE, CONTRADICTION))

        # `{'skip': <bool>}` -> `{'skip': lambda: <bool>}`
        self.simplifications.append((AND(IS_NOT_DICT, IS_NOT_CALLABLE), IDENTITY_FACTORY))

        self.simplifications.append((IS_NOT_DICT, _TRANSFORM_WHEN_NOT_DICT))

        # `{'skip': {VALUE: ...}}` -> `{'skip': {VALUE: ..., ACTION: lambda: NONE}}`
        self.simplifications.append(
            (AND(IS_DICT, _MISSING_ACTION), _TRANSFORM_WHEN_MISSING_ACTION)
        )

        # `{'skip': {ACTION: ...}}` -> `{'skip': {VALUE: lambda: False, ACTION: ...}}`
        self.simplifications.append((AND(IS_DICT, _MISSING_VALUE), _TRANSFORM_WHEN_MISSING_VALUE))

    def _do_parse(self, value):
        self.verify(value)

        parsed = self.parse_with(value, [Action])

        parsed["_should_skip"] = value[VALUE]

        return parsed

    async def should_skip(self, executor) -> bool:
        if IS_CALLABLE(should_skip := self._should_skip):
            return await executor.submit(should_skip)
        else:
            return should_skip

    async def when_skip(self, executor):
        return await executor.submit(self._when_skip)

    async def _do_apply(self, context: MiddlewareContext):
        should_skip = await self.should_skip(context.executor)
        context.scoped.setmagic(self.name, should_skip)
        if should_skip:
            context.scoped.setmagic(VALUE, await self.when_skip(context.executor))
        else:
            await context.next()
        return context.scoped


SKIP = Skip.get_name()
