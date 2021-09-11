from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Dict, Optional, Union

import ray

from ..constants import LEVEL, LOG, LOGGER, VALUE
from .component import Component
from .execution_component import ExecutionComponent

if TYPE_CHECKING:
    from ..manager.manager import Manager
    from ..manager.service.scoping import Scope

TLogValue = Union[str, Callable[..., str]]
TLogLevel = Union[str, int]
TLogger = Union[logging.Logger, Callable[..., logging.Logger]]

TLogDictConfig = Dict[str, Union[TLogValue, TLogLevel, TLogger]]
TLogConfig = Union[TLogValue, TLogDictConfig]


class LoggingComponent(Component):
    """
    A component that writes specified value with provided logger.
    """

    KEY_NAME: ClassVar[str] = LOG
    VALUE_KEYNAME: ClassVar[str] = VALUE
    LEVEL_KEYNAME: ClassVar[str] = LEVEL
    LOGGER_KEYNAME: ClassVar[str] = LOGGER

    DEFAULT_LOGGING_LEVEL: ClassVar[int] = logging.DEBUG

    def __init__(
        self,
        value: TLogValue,
        level: TLogLevel = logging.DEBUG,
        logger: Optional[TLogger] = None,
        **kwargs: Any
    ):
        super().__init__(**kwargs)
        self.__set_value(value)
        self.__set_level(level)
        self.__set_logger(logger)

    @classmethod
    def of(cls, config: TLogConfig) -> LoggingComponent:
        if isinstance(config, dict):
            return cls(**config)
        else:
            return cls(value=config)

    def __set_value(self, value: TLogValue) -> None:
        self._value = None
        self._value_getter = None

        if isinstance(value, str):
            self._value = value
        else:
            self._value_getter = ExecutionComponent(value)

    def __resolve_value(self, manager: Manager) -> str:
        if self._value is not None:
            return self._value

        return self._value_getter.execute(manager)

    def __set_level(self, level: TLogLevel) -> None:
        if isinstance(level, str):
            level = getattr(logging, level.upper(), self.DEFAULT_LOGGING_LEVEL)

        self._level = level

    def __set_logger(self, logger: Optional[TLogger]):
        self._logger = None
        self._logger_getter = None

        if logger is not None:
            if callable(logger):
                self._logger_getter = ExecutionComponent(logger)
            else:
                self._logger = logger

    def __resolve_logger(self, manager: Manager) -> logging.Logger:
        if self._logger is not None:
            return self._logger

        if self._logger_getter is not None:
            return self._logger_getter.execute(manager)

        return manager.get_logger()

    def __execute_for_value(self, manager: Manager, scope: Scope) -> str:
        value = self.__resolve_value(manager)
        scope.set_magic_value(name=self.VALUE_KEYNAME, value=value)
        return value

    def __execute_for_level(self, manager: Manager, scope: Scope) -> int:
        level = self._level
        scope.set_magic_value(name=self.LEVEL_KEYNAME, value=level)
        return level

    def __execute_for_logger(self, msg: str, level: int, manager: Manager) -> Any:
        logger = self.__resolve_logger(manager)
        try:
            log_func = logger.log.remote
        except AttributeError:
            log_func = logger.log
        return log_func(level=level, msg=msg)

    def execute(self, manager: Manager) -> Any:
        with manager.scoped() as scope:
            msg = self.__execute_for_value(manager, scope)
            level = self.__execute_for_level(manager, scope)
            return self.__execute_for_logger(msg, level, manager)


class LoggingComponentCombineWrapper(LoggingComponent):
    """
    Same as LoggingComponent except it is made compatible with `combine` (initializable from a single argument).
    """

    def __init__(self, config: TLogDictConfig, **kwargs):
        super().__init__(**config, **kwargs)
