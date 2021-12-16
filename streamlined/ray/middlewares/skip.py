from functools import partial
from operator import contains
from typing import Dict

from streamlined.ray.common.constants import RETURN_FALSE

from ..common import (
    ACTION,
    AND,
    CONTRADICTION,
    IDENTITY_FACTORY,
    IS_DICT,
    IS_NONE,
    IS_NOT_CALLABLE,
    NOOP,
    VALUE,
)
from .middleware import Middleware
from .parser import Parser


def _MISSING_ACTION(value):
    return ACTION not in value


def _TRANSFORM_WHEN_MISSING_ACTION(value):
    value[ACTION] = NOOP


def _MISSING_VALUE(value):
    return VALUE not in value


def _TRANSFORM_WHEN_MISSING_VALUE(value):
    value[VALUE] = RETURN_FALSE


class Skip(Middleware, Parser):
    def _init_simplifications(self) -> None:
        super()._init_simplifications()

        # transform `{'skip': None}` to `{'skip': False}`
        self.simplifications.append((IS_NONE, CONTRADICTION))

        # transform `{'skip': <bool>}` to `{'skip': lambda: <bool>}`
        self.simplifications.append((IS_NOT_CALLABLE, IDENTITY_FACTORY))

        # transform `{'skip': {VALUE: ...}}` to `{'skip': {VALUE: ..., ACTION: lambda: NONE}}`
        self.simplifications.append(
            (AND(IS_DICT, _MISSING_ACTION), _TRANSFORM_WHEN_MISSING_ACTION)
        )

        # transform `{'skip': {ACTION: ...}}` to `{'skip': {VALUE: lambda: False, ACTION: ...}}`
        self.simplifications.append((AND(IS_DICT, _MISSING_VALUE), _TRANSFORM_WHEN_MISSING_VALUE))
