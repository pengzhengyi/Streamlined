from typing import Any, Callable, Dict, List

from ..common import (
    AND,
    DEFAULT_KEYERROR,
    IS_CALLABLE,
    IS_DICT,
    IS_NOT_DICT,
    IS_NOT_LIST_OF_DICT,
)
from ..services import Scoped
from .argument import Arguments
from .cleanup import Cleanup
from .log import Log
from .middleware import (
    APPLY_INTO,
    APPLY_ONTO,
    Context,
    Middleware,
    StackMiddleware,
    WithMiddlewares,
)
from .name import NAME, Name
from .parser import Parser
from .runstep import (
    _MISSING_RUNSTEP_NAME,
    _TRANSFORM_WHEN_MISSING_NAME,
    _TRANSFORM_WHEN_RUNSTEPS_IS_DICT,
    RUNSTEPS,
    Runsteps,
)
from .setup import Setup
from .skip import Skip
from .validator import Validator

_MISSING_RUNSTAGE_NAME = _MISSING_RUNSTEP_NAME


def _MISSING_RUNSTAGE_RUNSTEPS(value: Dict[str, Any]) -> bool:
    return RUNSTEPS not in value


class Runstage(Parser, Middleware, WithMiddlewares):
    @classmethod
    def verify(cls, value: Any) -> None:
        super().verify(value)

        if IS_NOT_DICT(value):
            raise TypeError(f"{value} should be dict")

        if _MISSING_RUNSTAGE_NAME(value):
            raise DEFAULT_KEYERROR(value, NAME)

        if _MISSING_RUNSTAGE_RUNSTEPS(value):
            raise DEFAULT_KEYERROR(value, RUNSTEPS)

    def _init_middleware_types(self) -> None:
        super()._init_middleware_types()
        self.middleware_types.extend(
            [Name, Skip, Arguments, Setup, Validator, Runsteps, Log, Cleanup]
        )

    def _init_middleware_apply_methods(self) -> None:
        super()._init_middleware_apply_methods()
        self.middleware_apply_methods.extend(
            [
                APPLY_ONTO,
                APPLY_ONTO,
                APPLY_INTO,
                APPLY_ONTO,
                APPLY_ONTO,
                APPLY_ONTO,
                APPLY_ONTO,
                APPLY_ONTO,
            ]
        )

    def _init_simplifications(self) -> None:
        super()._init_simplifications()

        # `{RUNSTAGE: {...}}` -> `{RUNSTAGE: {.., NAME: <uuid>}}`
        self.simplifications.append(
            (AND(IS_DICT, _MISSING_RUNSTAGE_NAME), _TRANSFORM_WHEN_MISSING_NAME)
        )

    def _do_parse(self, value: Any) -> Dict[str, List[Middleware]]:
        self.verify(value)
        return {"middlewares": list(self.create_middlewares_from(value))}

    async def _do_apply(self, context: Context) -> Scoped:
        coroutine = WithMiddlewares.apply(self, context)
        return await coroutine()


RUNSTAGE = Runstage.get_name()

_TRANSFORM_WHEN_RUNSTAGES_IS_DICT = _TRANSFORM_WHEN_RUNSTEPS_IS_DICT


def _TRANSFORM_WHEN_RUNSTAGES_IS_CALLABLE(value: Callable[..., Any]) -> Dict[str, Any]:
    return {RUNSTEPS: value}


class Runstages(Parser, Middleware, StackMiddleware):
    @classmethod
    def verify(cls, value: Any) -> None:
        super().verify(value)

        if IS_NOT_LIST_OF_DICT(value):
            raise TypeError(f"{value} should be list of dict")

    def _init_simplifications(self) -> None:
        super()._init_simplifications()

        # `{RUNSTAGES: <callable>}` -> `{RUNSTAGES: {RUNSTEPS: <callable>}}`
        self.simplifications.append((IS_CALLABLE, _TRANSFORM_WHEN_RUNSTAGES_IS_CALLABLE))

        # `{RUNSTAGES: {...}}` -> `{RUNSTAGES: [{...}]}`
        self.simplifications.append((IS_DICT, _TRANSFORM_WHEN_RUNSTAGES_IS_DICT))

    def _do_parse(self, value: Any) -> Dict[str, Any]:
        self.verify(value)
        return {"middlewares": list(self.create_middlewares_from(value))}

    async def _do_apply(self, context: Context) -> Scoped:
        coroutine = StackMiddleware.apply_onto(self, context)
        return await coroutine()


RUNSTAGES = Runstages.get_name()