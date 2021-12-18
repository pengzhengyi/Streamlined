import logging
from typing import TYPE_CHECKING, Any, Awaitable, Dict, Optional

from ..common import (
    AND,
    IS_CALLABLE,
    IS_DICT,
    IS_STR,
    LEVEL,
    LOGGER,
    MESSAGE,
    get_or_raise,
)
from ..services import Scoped
from .middleware import Middleware, MiddlewareContext
from .parser import Parser


def _TRANSFORM_WHEN_IS_STR(value: str) -> Dict[str, Any]:
    return {MESSAGE: value}


def _MISSING_MESSAGE(value):
    return MESSAGE not in value


def _MISSING_LEVEL(value):
    return LEVEL not in value


def _TRANSFORM_WHEN_MISSING_LEVEL(value):
    value[LEVEL] = logging.DEBUG
    return value


def _MISSING_LOGGER(value):
    return LOGGER not in value


def _TRANSFORM_WHEN_MISSING_LOGGER(value):
    value[LOGGER] = logging.getLogger
    return value


_TRANSFORM_WHEN_IS_CALLABLE = _TRANSFORM_WHEN_IS_STR


class Log(Parser, Middleware):
    def _init_simplifications(self) -> None:
        super()._init_simplifications()

        # `{'log': <str>}` -> `{'log': {MESSAGE: <str>}}`
        self.simplifications.append((IS_STR, _TRANSFORM_WHEN_IS_STR))

        # `{'log': <callable>}` -> `{'log': {MESSAGE: <callable>}}`
        self.simplifications.append((IS_CALLABLE, _TRANSFORM_WHEN_IS_CALLABLE))

        # `{'log': {MESSAGE: ..., LOGGER: ...}}` -> `{'log': {MESSAGE: ..., LOGGER: ..., LEVEL: DEBUG}}`
        self.simplifications.append((AND(IS_DICT, _MISSING_LEVEL), _TRANSFORM_WHEN_MISSING_LEVEL))

        # `{'log': {MESSAGE: ..., LEVEL: ...}}` -> `{'log': {MESSAGE: ..., LOGGER: logging.getLogger, LEVEL: ...}}`
        self.simplifications.append(
            (AND(IS_DICT, _MISSING_LOGGER), _TRANSFORM_WHEN_MISSING_LOGGER)
        )

    def _do_parse(self, value: Dict[str, Any]) -> Dict:

        if not IS_DICT(value):
            raise TypeError(f"{value} should be dict")

        return {
            "_message": get_or_raise(value, MESSAGE),
            "_logger": get_or_raise(value, LOGGER),
            "_level": get_or_raise(value, LEVEL),
        }

    async def get_log_level(self, executor) -> int:
        if IS_CALLABLE(level := self._level):
            future = executor.submit(level)
            return await future
        else:
            return level

    async def get_logger(self, executor) -> logging.Logger:
        if IS_CALLABLE(logger := self._logger):
            future = executor.submit(logger)
            return await future
        else:
            return logger

    async def get_message(self, executor) -> str:
        if IS_CALLABLE(message := self._message):
            future = executor.submit(message)
            return await future
        else:
            return message

    async def _do_apply(self, context: MiddlewareContext) -> Awaitable[Optional[Scoped]]:
        message = await self.get_message(context.executor)
        context.scoped.setmagic(MESSAGE, message)

        level = await self.get_log_level(context.executor)
        context.scoped.setmagic(LEVEL, level)

        logger = await self.get_logger(context.executor)
        logger.log(level, message)

        await context.next()
        return context.scoped


LOG = Log.get_name()
