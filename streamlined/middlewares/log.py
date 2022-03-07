import logging
from functools import partial
from typing import Any, Dict, List, Tuple

from ..common import (
    AND,
    DEFAULT_KEYERROR,
    IDENTITY_FACTORY,
    IS_CALLABLE,
    IS_DICT,
    IS_DICT_MISSING_KEY,
    IS_NOT_CALLABLE,
    IS_STR,
    LEVEL,
    LOGGER,
    MESSAGE,
    VALUE,
    Predicate,
    Transform,
)
from ..services import Scoped
from .action import Action
from .middleware import Context, Middleware


def _TRANSFORM_WHEN_IS_STR(value: str) -> Dict[str, Any]:
    return {MESSAGE: value}


_MISSING_MESSAGE = partial(IS_DICT_MISSING_KEY, key=MESSAGE)


_MISSING_LEVEL = partial(IS_DICT_MISSING_KEY, key=LEVEL)


def _TRANSFORM_WHEN_MISSING_LEVEL(value: Dict[str, Any]) -> Dict[str, Any]:
    value[LEVEL] = logging.DEBUG
    return value


_MISSING_LOGGER = partial(IS_DICT_MISSING_KEY, key=LOGGER)


def _GET_DEFAULT_LOGGER(_scoped_: Scoped) -> logging.Logger:
    """
    If a scope is defined in any enclosing scopes, use that logger.
    Otherwise, use root logger.
    """
    try:
        return _scoped_.getmagic(LOGGER)
    except KeyError:
        return logging.getLogger()


def _TRANSFORM_WHEN_MISSING_LOGGER(value: Dict[str, Any]) -> Dict[str, Any]:
    value[LOGGER] = _GET_DEFAULT_LOGGER
    return value


def _MESSAGE_IS_STR(value: Dict[str, Any]) -> bool:
    return IS_STR(value[MESSAGE])


def _TRANSFORM_WHEN_MESSAGE_IS_STR(value: Dict[str, Any]) -> Dict[str, Any]:
    value[MESSAGE] = IDENTITY_FACTORY(value[MESSAGE])
    return value


def _LEVEL_NOT_CALLABLE(value: Dict[str, Any]) -> bool:
    return IS_NOT_CALLABLE(value[LEVEL])


def _TRANSFORM_WHEN_LEVEL_NOT_CALLABLE(value: Dict[str, Any]) -> Dict[str, Any]:
    value[LEVEL] = IDENTITY_FACTORY(value[LEVEL])
    return value


def _LOGGER_NOT_CALLABLE(value: Dict[str, Any]) -> bool:
    return IS_NOT_CALLABLE(value[LOGGER])


def _TRANSFORM_WHEN_LOGGER_NOT_CALLABLE(value: Dict[str, Any]) -> Dict[str, Any]:
    value[LOGGER] = IDENTITY_FACTORY(value[LOGGER])
    return value


_TRANSFORM_WHEN_IS_CALLABLE = _TRANSFORM_WHEN_IS_STR


class Log(Middleware):
    @classmethod
    def _get_simplifications(cls) -> List[Tuple[Predicate, Transform]]:
        simplifications = super()._get_simplifications()

        # `{'log': <str>}` -> `{'log': {MESSAGE: <str>}}`
        simplifications.append((IS_STR, _TRANSFORM_WHEN_IS_STR))

        # `{'log': <callable>}` -> `{'log': {MESSAGE: <callable>}}`
        simplifications.append((IS_CALLABLE, _TRANSFORM_WHEN_IS_CALLABLE))

        # `{'log': {MESSAGE: ..., LOGGER: ...}}` -> `{'log': {MESSAGE: ..., LOGGER: ..., LEVEL: DEBUG}}`
        simplifications.append((AND(IS_DICT, _MISSING_LEVEL), _TRANSFORM_WHEN_MISSING_LEVEL))

        # `{'log': {MESSAGE: ..., LEVEL: ...}}` -> `{'log': {MESSAGE: ..., LOGGER: _GET_DEFAULT_LOGGER, LEVEL: ...}}`
        simplifications.append((AND(IS_DICT, _MISSING_LOGGER), _TRANSFORM_WHEN_MISSING_LOGGER))

        # `{'log': {MESSAGE: <str>, LOGGER: ..., LEVEL: ...}}` -> `{'log': {MESSAGE: IDENTITY_FACTORY(<str>), LOGGER: ..., LEVEL: ...}}`
        simplifications.append((AND(IS_DICT, _MESSAGE_IS_STR), _TRANSFORM_WHEN_MESSAGE_IS_STR))

        # `{'log': {MESSAGE: ..., LOGGER: ..., LEVEL: <int>}}` -> `{'log': {MESSAGE: ..., LOGGER: ..., LEVEL: IDENTITY_FACTORY(<int>)}}`
        simplifications.append(
            (AND(IS_DICT, _LEVEL_NOT_CALLABLE), _TRANSFORM_WHEN_LEVEL_NOT_CALLABLE)
        )

        # `{'log': {MESSAGE: ..., LOGGER: <logger> LEVEL: ...}}` -> `{'log': {MESSAGE: ..., LOGGER: IDENTITY_FACTORY(<logger>), LEVEL: ...)}}`
        simplifications.append(
            (AND(IS_DICT, _LOGGER_NOT_CALLABLE), _TRANSFORM_WHEN_LOGGER_NOT_CALLABLE)
        )
        return simplifications

    @classmethod
    def verify(cls, value: Any) -> None:
        super().verify(value)

        if not IS_DICT(value):
            raise TypeError(f"{value} should be dict")

        if _MISSING_LEVEL(value):
            raise DEFAULT_KEYERROR(value, LEVEL)

        if _MISSING_LOGGER(value):
            raise DEFAULT_KEYERROR(value, LOGGER)

        if _MISSING_MESSAGE(value):
            raise DEFAULT_KEYERROR(value, MESSAGE)

    def _do_parse(self, value: Dict[str, Any]) -> Dict[str, Middleware]:
        self.verify(value)

        parsed: Dict[str, Middleware] = dict()
        for keyname in [LOGGER, LEVEL, MESSAGE]:
            parsed[keyname] = Action(value[keyname])

        return parsed

    async def get_log_level(self, context: Context) -> int:
        scoped = await Middleware.apply_onto(
            getattr(self, LEVEL), context.replace_with_void_next()
        )
        level = scoped.getmagic(VALUE)
        context.scoped.setmagic(LEVEL, level)
        return level

    async def get_logger(self, context: Context) -> logging.Logger:
        scoped = await Middleware.apply_onto(
            getattr(self, LOGGER), context.replace_with_void_next()
        )
        logger = scoped.getmagic(VALUE)
        context.scoped.setmagic(LOGGER, logger, 1)
        return logger

    async def get_message(self, context: Context) -> str:
        scoped = await Middleware.apply_onto(
            getattr(self, MESSAGE), context.replace_with_void_next()
        )
        message = scoped.getmagic(VALUE)
        context.scoped.setmagic(MESSAGE, message)
        return message

    async def _do_apply(self, context: Context) -> Scoped:
        message = await self.get_message(context)

        level = await self.get_log_level(context)

        logger = await self.get_logger(context)
        logger.log(level, message)

        await context.next()
        return context.scoped


LOG = Log.get_name()
