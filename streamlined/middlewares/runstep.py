import uuid
from typing import Any, Callable, Dict, List, Union

from ..common import (
    AND,
    DEFAULT_KEYERROR,
    IS_CALLABLE,
    IS_DICT,
    IS_LIST,
    IS_NOT_CALLABLE,
    IS_NOT_DICT,
    IS_NOT_LIST,
    VALUE,
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


def _TRANSFORM_WHEN_RUNSTEP_IS_CALLABLE(value: Dict[str, Any]) -> Dict[str, Any]:
    return {ACTION: value}


def _TRANSFORM_WHEN_MISSING_NAME(value: Dict[str, Any]) -> Dict[str, Any]:
    value[NAME] = str(uuid.uuid4())
    return value


class Runstep(Middleware, WithMiddlewares):
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

        # `{RUNSTEP: <callable>}` -> `{RUNSTEP: {.., ACTION: <callable>}}`
        self.simplifications.append((IS_CALLABLE, _TRANSFORM_WHEN_RUNSTEP_IS_CALLABLE))

        # `{RUNSTEP: {...}}` -> `{RUNSTEP: {.., ACTION: VOID}}`
        self.simplifications.append(
            (AND(IS_DICT, _MISSING_RUNSTEP_ACTION), _TRANSFORM_WHEN_MISSING_ACTION)
        )

        # `{RUNSTEP: {...}}` -> `{RUNSTEP: {.., NAME: <uuid>}}`
        self.simplifications.append(
            (AND(IS_DICT, _MISSING_RUNSTEP_NAME), _TRANSFORM_WHEN_MISSING_NAME)
        )

    def _do_parse(self, value: Any) -> Dict[str, List[Middleware]]:
        self.verify(value)
        return {"middlewares": list(self.create_middlewares_from(value))}

    async def _do_apply(self, context: Context) -> Scoped:
        coroutine = WithMiddlewares.apply(self, context)
        return await coroutine()


RUNSTEP = Runstep.get_name()


def _TRANSFORM_WHEN_RUNSTEPS_IS_DICT(value: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [value]


class Runsteps(Middleware, StackMiddleware):
    middlewares_generator: Action

    @classmethod
    def verify(cls, value: Any) -> None:
        super().verify(value)

        if IS_NOT_LIST(value) and IS_NOT_CALLABLE(value):
            raise TypeError(f"{value} should be list or a callable returning a list")

    def _init_simplifications(self) -> None:
        super()._init_simplifications()

        # `{RUNSTEPS: {...}}` -> `{RUNSTEPS: [{...}]}`
        self.simplifications.append((IS_DICT, _TRANSFORM_WHEN_RUNSTEPS_IS_DICT))

    def _do_parse(
        self, value: Union[List[Dict[str, Any]], Callable[..., List[Dict[str, Any]]]]
    ) -> Dict[str, Any]:
        self.verify(value)
        if IS_LIST(value):
            return {"middlewares": list(self.create_middlewares_from(value))}
        else:
            # generate runsteps dynamically
            action = Action({ACTION: value})
            return {"middlewares_generator": action}

    async def _do_apply(self, context: Context) -> Scoped:
        if hasattr(self, "middlewares_generator"):
            scoped = await self.middlewares_generator.apply_onto(context.replace_with_void_next())
            runsteps: List[Dict[str, Any]] = scoped.getmagic(VALUE)
            self.middlewares = list(self.create_middlewares_from(runsteps))

        coroutine = StackMiddleware.apply_onto(self, context)
        return await coroutine()


RUNSTEPS = Runsteps.get_name()
