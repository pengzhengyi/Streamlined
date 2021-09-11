from __future__ import annotations

import logging
import sys
from typing import Any, Callable, Iterable, Optional, Set, Type

import ray

from ..component.proxies import Actor

# Mixins


def get_stdout_handler() -> logging.Handler:
    """Return a Handler that logs to stdout"""
    return logging.StreamHandler(sys.stdout)


def get_stderr_handler() -> logging.Handler:
    """Return a Handler that logs to stderr"""
    return logging.StreamHandler(sys.stderr)


def conditional_stream_mixin(
    logger_class: Type[logging.Logger],
) -> Type[logging.Logger]:
    """
    Create a ConditionalStreamLogger that subclasses provided logger class.
    """

    class ConditionalStreamLogger(logger_class):
        """
        A logger class that messages less severe than INFO will be logged to stdout and
        other to stderr.
        """

        def __init__(self, name: str, level: int = logging.NOTSET):
            super().__init__(name, level)

            self.stdout_handler = get_stdout_handler()
            self.stdout_handler.addFilter(lambda record: record.levelno <= logging.INFO)
            self.addHandler(self.stdout_handler)

            self.stderr_handler = get_stderr_handler()
            self.stderr_handler.setLevel(logging.WARN)
            self.addHandler(self.stderr_handler)

        def set_stdout_format(self, *args: Any, **kwargs: Any) -> None:
            """
            Set the formatter for stdout handler.

            See https://docs.python.org/3.8/library/logging.html#logging.Formatter
            for expected arguments.
            """
            self.stdout_handler.setFormatter(logging.Formatter(*args, **kwargs))

        def set_stderr_format(self, *args: Any, **kwargs: Any) -> None:
            """
            Set the formatter for stderr handler.

            See https://docs.python.org/3.8/library/logging.html#logging.Formatter
            for expected arguments.
            """
            self.stderr_handler.setFormatter(logging.Formatter(*args, **kwargs))

    return ConditionalStreamLogger


TLoggerMixin = Callable[[Type[logging.Logger]], Type[logging.Logger]]


# common


def create_logger_class(mixins: Optional[Iterable[TLoggerMixin]] = None) -> Type[logging.Logger]:
    """
    Create a logger class with provided mixins.

    A mixin should be a function that takes a logger class and return a logger class
    (usually a subclass).
    """
    logger_class = logging.getLoggerClass()
    if mixins is not None:
        for mixin in mixins:
            logger_class = mixin(logger_class)
    return logger_class


def create_logger(
    name: str, level: int = logging.NOTSET, mixins: Optional[Iterable[TLoggerMixin]] = None
) -> logging.Logger:
    """
    Create a logger instance with the specified name and level.

    If `mixins` is provided, the created logger will come from current logger class with
    all mixins applied.
    """
    return create_logger_class(mixins)(name, level)


DEFAULT_REMOTE_METHODS = set(["debug", "info", "warning", "error", "critical", "log", "exception"])


def create_async_logger(
    name: str,
    level: int = logging.NOTSET,
    mixins: Optional[Iterable[TLoggerMixin]] = None,
    remote_methods: Set[str] = DEFAULT_REMOTE_METHODS,
) -> logging.Logger:
    """
    Create a logger Actor instance with the specified name and level.

    [Actor](https://docs.ray.io/en/master/walkthrough.html?highlight=actor#remote-classes-actors)

    This logger is safe with multiple processes.

    If `mixins` is provided, the created logger will come from current logger class with
    all mixins applied.
    """
    logger_class = create_logger_class(mixins)
    logger = ray.remote(logger_class).remote(name, level)
    return Actor(logger, remote_methods)
