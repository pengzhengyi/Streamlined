import asyncio
import importlib
from asyncio.tasks import Task
from contextlib import suppress
from dataclasses import dataclass, replace
from functools import partial
from typing import Any, Dict, Iterable, List, Set, Type

from ..common import (
    AND,
    DEFAULT_KEYERROR,
    IDENTITY_FACTORY,
    IS_CALLABLE,
    IS_DICT,
    IS_DICT_MISSING_KEY,
    IS_LIST,
    IS_LIST_OF_DICT,
    IS_NOT_CALLABLE,
    IS_NOT_DICT,
    IS_NOT_LIST,
    IS_NOT_LIST_OF_DICT,
    VALUE,
)
from ..scheduling import SEQUENTIAL, Dependency, Parallel, Schedule, Scheduler, Unit
from ..services import Scoped
from .action import Action
from .middleware import APPLY_METHOD, APPLY_ONTO, Context, Middleware, WithMiddlewares

SCHEDULING = "scheduling"
CONCURRENCY = "concurrency"


@dataclass
class MiddlewareWithApplyMethod:
    middleware: Middleware
    apply_method: APPLY_METHOD


_MISSING_VALUE = partial(IS_DICT_MISSING_KEY, key=VALUE)


def _HAS_SCHEDULING(value: Dict[str, Any]) -> bool:
    return SCHEDULING in value


def _NEED_DEFAULT_SCHEDULING(value: Dict[str, Any]) -> bool:
    return IS_DICT_MISSING_KEY(value, SCHEDULING) and IS_DICT_MISSING_KEY(value, CONCURRENCY)


def _IS_CONCURRENCY_PRESENT_BUT_NOT_CALLABLE(value: Dict[str, Any]) -> bool:
    return CONCURRENCY in value and IS_NOT_CALLABLE(value[CONCURRENCY])


def _TRANSFORM_WHEN_IS_LIST_OF_DICT(value: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {VALUE: value}


_TRANSFORM_WHEN_IS_CALLABLE = _TRANSFORM_WHEN_IS_LIST_OF_DICT


def _TRANSFORM_WHEN_CONCURRENCY_PRESENT_BUT_NOT_CALLABLE(value: Dict[str, Any]) -> Dict[str, Any]:
    value[CONCURRENCY] = IDENTITY_FACTORY(value[CONCURRENCY])
    return value


def _TRANSFORM_WHEN_NEED_DEFAULT_SCHEDULING(value: Dict[str, Any]) -> Dict[str, Any]:
    value[SCHEDULING] = SEQUENTIAL
    return value


def _SCHEDULING_PRESENT_BUT_NOT_CALLABLE(value: Dict[str, Any]) -> bool:
    return SCHEDULING in value and IS_NOT_CALLABLE(value[SCHEDULING])


def _IS_SCHEDULING_LIST_BUT_NOT_LIST_OF_DEPENDENCY(value: Dict[str, Any]) -> bool:
    scheduling = value[SCHEDULING]
    return IS_LIST(scheduling) and any(
        not isinstance(dependency, Dependency) for dependency in scheduling
    )


def _TRANSFORM_WHEN_SCHEDULING_NOT_LIST_OF_DEPENDENCY(value: Dict[str, Any]) -> Dict[str, Any]:
    value[SCHEDULING] = [Dependency(*dependency) for dependency in value[SCHEDULING]]
    return value


def _IS_SCHEDULING_DEPENDENCY(value: Dict[str, Any]) -> bool:
    return isinstance(value[SCHEDULING], Dependency)


def _TRANSFORM_WHEN_SCHEDULING_IS_DEPENDENCY(value: Dict[str, Any]) -> Dict[str, Any]:
    value[SCHEDULING] = [value[SCHEDULING]]
    return value


def _TRANSFORM_WHEN_IS_NOT_LIST_OF_DICT(value: List[Any], typename: str) -> List[Dict[str, Any]]:
    new_value: List[Dict[str, Any]] = []

    for subvalue in value:
        if IS_NOT_DICT(subvalue) or typename not in subvalue:
            new_value.append({typename: subvalue})
        else:
            new_value.append(subvalue)

    return new_value


def _IS_SCHEDULING_LIST_OF_DEPENDENCY(value: Dict[str, Any]) -> bool:
    dependencies = value[SCHEDULING]
    return IS_LIST(dependencies) and all(
        isinstance(dependency, Dependency) for dependency in dependencies
    )


def _get_unit_identifiers(
    unit: Unit, unit_index: int, possible_identifier_names: List[str] = ["name", "key"]
) -> List[Any]:
    """Return a list of identifiers that can represent a unit."""
    identifiers = [unit, unit_index]
    for name in possible_identifier_names:
        try:
            identifiers.append(getattr(unit, name))
        except KeyError:
            continue

    return identifiers


def _resolve_dependencies(
    dependencies: List[Dependency[Any]], units: List[Unit]
) -> List[Dependency[Unit]]:
    """
    The passed-in `dependencies` might represent a unit in different ways:

    - a unit's index
    - a unit's name

    This method replace these identifiers with the represented unit so that
    the returned dependencies should only contain `Unit` in `dependent` and
    `prerequisite` fields.
    """
    for unit_index, unit in enumerate(units):
        new_dependencies: List[Dependency[Any]] = []
        unit_identifiers = _get_unit_identifiers(unit, unit_index)

        for dependency in dependencies:
            if dependency.dependent in unit_identifiers:
                dependency = replace(dependency, dependent=unit)
            if dependency.prerequisite in unit_identifiers:
                dependency = replace(dependency, prerequisite=unit)
            new_dependencies.append(dependency)
        dependencies = new_dependencies

    return dependencies


def _TRANSFORM_SCHEDULING_WHEN_IS_LIST_OF_REQUIREMENT(value: Dict[str, Any]) -> Dict[str, Any]:
    has_prerequisites: Set[Any] = set()
    has_dependents: Set[Any] = set()

    dependencies: List[Dependency[Any]] = value[SCHEDULING]

    for dependency in dependencies:
        has_prerequisites.add(dependency.dependent)
        has_dependents.add(dependency.prerequisite)

    def generate_schedule(units: List[Unit]) -> Schedule:
        schedule = Schedule()

        for unit_index, unit in enumerate(units):
            identifiers = _get_unit_identifiers(unit, unit_index)

            schedule.push(
                unit,
                has_prerequisites=any(
                    identifier in has_prerequisites for identifier in identifiers
                ),
                has_dependents=any(identifier in has_dependents for identifier in identifiers),
            )

        resolved_dependencies = _resolve_dependencies(dependencies, units)
        for dependency in resolved_dependencies:
            dependency.dependent.require(
                dependency.prerequisite, dependency.condition, dependency.group
            )

        return schedule

    value[SCHEDULING] = generate_schedule
    return value


class ScheduledMiddlewares(Middleware, WithMiddlewares):
    middlewares_generator: Action
    scheduler: Scheduler
    concurrency: Action

    middlewares: List[Middleware]
    middleware_schedule: Schedule

    @classmethod
    def verify(cls, value: Any) -> None:
        super().verify(value)

        if IS_NOT_DICT(value):
            raise TypeError(f"{value} should be dict")

        if _NEED_DEFAULT_SCHEDULING(value):
            raise DEFAULT_KEYERROR(value, SCHEDULING)
        elif _SCHEDULING_PRESENT_BUT_NOT_CALLABLE(value):
            raise ValueError(f"{SCHEDULING} should be a callable generating a schedule")

        if _MISSING_VALUE(value):
            raise DEFAULT_KEYERROR(value, VALUE)
        elif IS_NOT_LIST(value[VALUE]) and IS_NOT_CALLABLE(value[VALUE]):
            raise TypeError(f"{value[VALUE]} should be list or a callable returning a list")

        if _IS_CONCURRENCY_PRESENT_BUT_NOT_CALLABLE(value):
            raise ValueError(f"{CONCURRENCY} is present but not a callable")

        if CONCURRENCY in value and SCHEDULING in value:
            raise ValueError(f"only one of {CONCURRENCY} and {SCHEDULING}can be specified")

    def _init_simplifications(self) -> None:
        super()._init_simplifications()

        # `<callable>` -> `{VALUE: <callable>}`
        self.simplifications.append((IS_CALLABLE, _TRANSFORM_WHEN_IS_CALLABLE))

        # `[{...}]` -> `{VALUE: [{...}]}`
        self.simplifications.append((IS_LIST_OF_DICT, _TRANSFORM_WHEN_IS_LIST_OF_DICT))

        # `{VALUE: [{...}], CONCURRENCY: <int>}` -> `{VALUE: [{...}], CONCURRENCY: IDENTITY_FACTORY(<int>)}`
        self.simplifications.append(
            (
                AND(IS_DICT, _IS_CONCURRENCY_PRESENT_BUT_NOT_CALLABLE),
                _TRANSFORM_WHEN_CONCURRENCY_PRESENT_BUT_NOT_CALLABLE,
            )
        )

        # `{VALUE: [{...}]}` -> `{VALUE: [{...}], SCHEDULING: SEQUENTIAL}`
        self.simplifications.append(
            (AND(IS_DICT, _NEED_DEFAULT_SCHEDULING), _TRANSFORM_WHEN_NEED_DEFAULT_SCHEDULING)
        )

        # `{VALUE: [{...}], SCHEDULING: [(..., ...)]}` -> `{VALUE: [{...}], SCHEDULING: [(..., ..., None, None)]}`
        self.simplifications.append(
            (
                AND(IS_DICT, _HAS_SCHEDULING, _IS_SCHEDULING_LIST_BUT_NOT_LIST_OF_DEPENDENCY),
                _TRANSFORM_WHEN_SCHEDULING_NOT_LIST_OF_DEPENDENCY,
            )
        )

        # `{VALUE: [{...}], {SCHEDULING: <dependency>}}` -> `{VALUE: [{...}], {SCHEDULING: [<dependency>]}}`
        self.simplifications.append(
            (
                AND(IS_DICT, _HAS_SCHEDULING, _IS_SCHEDULING_DEPENDENCY),
                _TRANSFORM_WHEN_SCHEDULING_IS_DEPENDENCY,
            )
        )

        # `{VALUE: [{...}], {SCHEDULING: [<dependency>]}}` -> `{SCHEDULING: <SCHEDULE_GENERATOR>}`
        self.simplifications.append(
            (
                AND(IS_DICT, _HAS_SCHEDULING, _IS_SCHEDULING_LIST_OF_DEPENDENCY),
                _TRANSFORM_SCHEDULING_WHEN_IS_LIST_OF_REQUIREMENT,
            )
        )

    def _get_middleware_units(self) -> List[Unit]:
        return [
            Unit(MiddlewareWithApplyMethod(middleware, apply_method))
            for middleware, apply_method in zip(self.middlewares, self.apply_methods)
        ]

    def _do_parse(self, value: Dict[str, Any]) -> Dict[str, Any]:
        parsed = {
            "middlewares_generator": Action(value[VALUE]),
        }
        if SCHEDULING in value:
            parsed["scheduler"] = value[SCHEDULING]
        if CONCURRENCY in value:
            parsed["concurrency"] = Action(value[CONCURRENCY])

        return parsed

    async def _init_scheduler(self, context: Context) -> None:
        with suppress(AttributeError):
            scoped = await self.concurrency.apply_onto(context.replace_with_void_next())
            concurrency: int = scoped.getmagic(VALUE)
            context.scoped.update(scoped)
            context.scoped.setmagic(CONCURRENCY, concurrency)
            self.scheduler = Parallel(concurrency)

    async def _init_schedule(self, context: Context) -> None:
        scoped = await self.middlewares_generator.apply_onto(context.replace_with_void_next())
        middleware_configs = scoped.getmagic(VALUE)

        context.scoped.update(scoped)

        self.middlewares = list(self.create_middlewares_from(middleware_configs))
        self.middleware_units = self._get_middleware_units()
        self.middleware_schedule = self.scheduler(self.middleware_units)

    async def _do_apply(self, context: Context) -> Scoped:
        await self._init_scheduler(context)
        await self._init_schedule(context)

        def create_task(unit: Unit) -> "Task[Scoped]":
            return asyncio.create_task(
                Middleware.apply(
                    unit.middleware,
                    context.replace_with_void_next(),
                    unit.apply_method,
                )
            )

        async for scoped in self.middleware_schedule.work_greedy(create_task):
            context.scoped.update(scoped)

        return await context.next()


class StackedMiddlewares(ScheduledMiddlewares):
    """
    StackMiddleware means middleware of same type is stacked --
    multiple instances of this middleware type is initialized.

    The value to parse should be a list of dictionary where each
    dictionary is parseable by that middleware type.

    At its application, the initialized instances will be applied in list order.

    When `_init_stacked_middleware_type` is not overridden, the
    default typename will be current class name without ending 's'
    and type will be resolved dynamically by looking at class defined
    in same module name.
    """

    @classmethod
    def _get_inferred_stacked_middleware_name(cls) -> str:
        self_name = cls.__name__

        if self_name.endswith("s"):
            return self_name[:-1]

        raise ValueError("Cannot infer middleware name to stack")

    def __convert_middleware_typename_to_type(self, name: str) -> Type[Middleware]:
        current_module_path = __name__
        parent_module_path = current_module_path[: current_module_path.rindex(".")]
        module = importlib.import_module(f".{name.lower()}", parent_module_path)
        return getattr(module, name)

    def __init_stacked_middleware_type(self) -> Type[Middleware]:
        self.__middleware_typename = self._get_inferred_stacked_middleware_name()
        self.__middleware_type = self.__convert_middleware_typename_to_type(
            self.__middleware_typename
        )

    def _init_simplifications(self) -> None:
        super()._init_simplifications()

        # `[{...}]` -> `{VALUE: [{...}]}`
        self.__init_stacked_middleware_type()
        typename: str = self.__middleware_type.get_name()

        self.simplifications.insert(
            1,
            (
                AND(IS_LIST, IS_NOT_LIST_OF_DICT),
                partial(
                    _TRANSFORM_WHEN_IS_NOT_LIST_OF_DICT,
                    typename=typename,
                ),
            ),
        )

    def _init_middleware_types(self) -> None:
        super()._init_middleware_types()
        self.middleware_types.append(self.__middleware_type)

    def _init_middleware_apply_methods(self) -> None:
        self.middleware_apply_methods = APPLY_ONTO

    def create_middlewares_from(self, value: List[Dict[str, Any]]) -> Iterable[Middleware]:
        for middleware_type, middleware_name in zip(
            self.middleware_types, self.get_middleware_names()
        ):
            for argument_value in value:
                yield middleware_type.of(argument_value, name=middleware_name)
