import uuid
from typing import Any, Awaitable, Callable, Dict, List

from ..common import (
    AND,
    DEFAULT_KEYERROR,
    IS_CALLABLE,
    IS_DICT,
    IS_NOT_DICT,
    IS_NOT_LIST_OF_DICT,
    VOID,
)
from ..services import Scoped
from .action import ACTION, Action
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
from .setup import Setup
from .skip import Skip
from .validator import Validator


def _MISSING_RUNSTEP_NAME(value: Dict[str, Any]) -> bool:
    return NAME not in value


def _MISSING_RUNSTEP_ACTION(value: Dict[str, Any]) -> bool:
    return ACTION not in value


def _TRANSFORM_WHEN_MISSING_ACTION(value: Dict[str, Any]) -> Dict[str, Any]:
    value[ACTION] = VOID
    return value


def _TRANSFORM_WHEN_MISSING_NAME(value: Dict[str, Any]) -> Dict[str, Any]:
    value[NAME] = str(uuid.uuid4())
    return value


class Runstep(Parser, Middleware, WithMiddlewares):
    @classmethod
    def verify(cls, value: Any) -> None:
        super().verify(value)

        if IS_NOT_DICT(value):
            raise TypeError(f"{value} should be dict")

        if _MISSING_RUNSTEP_NAME(value):
            raise DEFAULT_KEYERROR(value, NAME)

        if _MISSING_RUNSTEP_ACTION(value):
            raise DEFAULT_KEYERROR(value, ACTION)

    def _init_middleware_types(self) -> None:
        super()._init_middleware_types()
        self.middleware_types.extend(
            [Name, Skip, Arguments, Setup, Validator, Action, Log, Cleanup]
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
                APPLY_INTO,
                APPLY_ONTO,
                APPLY_ONTO,
            ]
        )

    def _init_simplifications(self) -> None:
        super()._init_simplifications()

        # `{RUNSTEP: {...}}` -> `{RUNSTEP: {.., ACTION: VOID}}`
        self.simplifications.append(
            (AND(IS_DICT, _MISSING_RUNSTEP_ACTION), _TRANSFORM_WHEN_MISSING_ACTION)
        )

        # `{RUNSTEP: {...}}` -> `{RUNSTEP: {.., NAME: <uuid>}}`
        self.simplifications.append(
            (AND(IS_DICT, _MISSING_RUNSTEP_NAME), _TRANSFORM_WHEN_MISSING_NAME)
        )

    def _do_parse(self, value: Any) -> Dict:
        self.verify(value)
        return {"middlewares": list(self.create_middlewares_from(value))}

    async def _do_apply(self, context: Context) -> Awaitable[Scoped]:
        coroutine = WithMiddlewares.apply(self, context)
        return await coroutine()


RUNSTEP = Runstep.get_name()


def _TRANSFORM_WHEN_RUNSTEPS_IS_CALLABLE(value: Callable[..., Any]) -> Dict[str, Any]:
    return {ACTION: value}


def _TRANSFORM_WHEN_RUNSTEPS_IS_DICT(value: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [value]


class Runsteps(Parser, Middleware, StackMiddleware):
    @classmethod
    def verify(cls, value: Any) -> None:
        super().verify(value)

        if IS_NOT_LIST_OF_DICT(value):
            raise TypeError(f"{value} should be list of dict")

    def _init_simplifications(self) -> None:
        super()._init_simplifications()

        # `{RUNSTEPS: <callable>}` -> `{RUNSTEPS: {ACTION: <callable>}}`
        self.simplifications.append((IS_CALLABLE, _TRANSFORM_WHEN_RUNSTEPS_IS_CALLABLE))

        # `{RUNSTEPS: {...}}` -> `{RUNSTEPS: [{...}]}`
        self.simplifications.append((IS_DICT, _TRANSFORM_WHEN_RUNSTEPS_IS_DICT))

    def _do_parse(self, value: Any) -> Dict[str, Any]:
        self.verify(value)
        return {"middlewares": list(self.create_middlewares_from(value))}

    async def _do_apply(self, context: Context) -> Scoped:
        coroutine = StackMiddleware.apply_onto(self, context)
        return await coroutine()


RUNSTEPS = Runsteps.get_name()
