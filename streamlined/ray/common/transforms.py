from functools import partial
from typing import Any, Callable

Transform = Callable[[Any], Any]


def IDENTITY(value):
    return value


def IDENTITY_FACTORY(value):
    return partial(IDENTITY, value)
