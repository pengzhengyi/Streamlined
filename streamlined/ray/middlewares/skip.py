from typing import Callable

from ..common import (
    ACTION,
    AND,
    CONTRADICTION,
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
from .middleware import Middleware
from .parser import NestedParser


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


class Skip(NestedParser, Middleware):
    @property
    def _when_skip(self) -> Callable:
        return self._action

    def _init_subparsers(self) -> None:
        super()._init_subparsers()
        self.subparsers.append(Action)

    def _init_simplifications(self) -> None:
        super()._init_simplifications()

        # transform `{'skip': None}` to `{'skip': False}`
        self.simplifications.append((IS_NONE, CONTRADICTION))

        # transform `{'skip': <bool>}` to `{'skip': lambda: <bool>}`
        self.simplifications.append((AND(IS_NOT_DICT, IS_NOT_CALLABLE), IDENTITY_FACTORY))

        self.simplifications.append((IS_NOT_DICT, _TRANSFORM_WHEN_NOT_DICT))

        # transform `{'skip': {VALUE: ...}}` to `{'skip': {VALUE: ..., ACTION: lambda: NONE}}`
        self.simplifications.append(
            (AND(IS_DICT, _MISSING_ACTION), _TRANSFORM_WHEN_MISSING_ACTION)
        )

        # transform `{'skip': {ACTION: ...}}` to `{'skip': {VALUE: lambda: False, ACTION: ...}}`
        self.simplifications.append((AND(IS_DICT, _MISSING_VALUE), _TRANSFORM_WHEN_MISSING_VALUE))

    def _do_parse(self, value):
        parsed = dict()

        if not IS_DICT(value):
            raise TypeError(f"{value} should be dict")

        if _MISSING_VALUE(value):
            raise ValueError(f"{value} should have {VALUE} property")
        else:
            parsed["should_skip"] = value[VALUE]

        if _MISSING_ACTION(value):
            raise ValueError(f"{value} should have {ACTION} property")
        else:
            parsed.update(super()._do_parse(value))

        return parsed

    async def should_skip(self, executor) -> bool:
        if IS_CALLABLE(self._should_skip):
            future = executor.submit(self._should_skip)
            return await future
        else:
            return self._should_skip

    async def when_skip(self, executor):
        future = executor.submit(self._when_skip)
        return await future

    async def _do_apply(self, executor, next):
        if await self.should_skip(executor):
            await self.when_skip(executor)
        else:
            await next()


SKIP = Skip.get_name()
