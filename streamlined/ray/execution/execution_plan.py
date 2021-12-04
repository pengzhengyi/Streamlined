from __future__ import annotations

import asyncio
from functools import partial
from typing import Any, Callable, ClassVar, Dict, Iterable, Optional, Type, Union

import networkx as nx

from ..common import ASYNC_VOID, VOID
from ..services import DependencyTracking, EventNotification
from .execution_requirements import ExecutionRequirements
from .execution_unit import AsyncExecutionUnit, ExecutionUnit
from .executor import RayExecutor


class DependencyTrackingExecutionUnit(DependencyTracking, ExecutionUnit):
    """
    Beyond plain `ExecutionUnit` and `DependencyTracking`, this provides EventNotification when all prerequisites are satisfied and when execution completed.
    """

    REQUIREMENTS_FACTORY: ClassVar[Type[ExecutionRequirements]] = ExecutionRequirements
    _requirements: ExecutionRequirements

    def __init__(self, _callable: Callable = VOID):
        super().__init__(_callable=_callable)

    def require(
        self,
        prerequisite: DependencyTrackingExecutionUnit,
        group: Optional[Union[Any, Iterable[Any]]] = None,
        condition: Optional[Callable[[], bool]] = None,
    ):
        if condition:
            self._requirements.conditions[prerequisite] = condition
        if group:
            try:
                for _group in group:
                    self.add_to_group(prerequisite, _group)
            except TypeError:
                self.add_to_group(prerequisite, group)
        return super().require(prerequisite)

    def add_to_group(self, prerequisite: DependencyTrackingExecutionUnit, group: Any) -> None:
        """
        Add a prerequisite into a requirement group.

        When all prerequisites in a requirement group are satisfied, the requirements of this execution unit is considered satisfied.

        All prerequisites are automatically in a default requirement group.
        """
        self._requirements.groups[group] = prerequisite

    @property
    def on_new_requirement(self) -> EventNotification:
        return self._requirements.on_new_requirement

    @property
    def on_requirements_satisfied(self) -> EventNotification:
        return self._requirements.on_requirements_satisfied


class DependencyTrackingAsyncExecutionUnit(AsyncExecutionUnit, DependencyTrackingExecutionUnit):
    """
    Similar as ExecutionUnit, but work specifically for coroutines.
    """

    def __init__(self, _callable: Callable = ASYNC_VOID):
        super().__init__(_callable=_callable)


class DependencyTrackingRayExecutionUnit(DependencyTrackingAsyncExecutionUnit):
    def __init__(self, _callable=ASYNC_VOID, ray_options: Optional[Dict[str, Any]] = None):
        super().__init__(_callable=_callable)
        self._ray_options = ray_options

    def _init_task(self, _callable: Any):
        if asyncio.iscoroutinefunction(_callable):
            _callable, self._coroutine_actor = RayExecutor.to_remote_function(_callable)

        return super()._init_task(_callable)

    async def _execute(self, *args, **kwargs):
        return await RayExecutor.run(
            self._callable, *args, ray_options=self._ray_options, **kwargs
        )


class ExecutionPlan:
    """
    ExecutionPlan can be seen as a Graph of ExecutionUnit.

    More specifically, nodes are callables while edges are execution dependency relationships.

    Events
    --------
    ExecutionPlan also exposes two events:

    + `on_requirements_satisfied(execution_unit, prerequisite)` This event signals an execution unit is ready to execute
    + `on_complete(result, execution_unit)` This event notifies an execution unit has completed its execution.

    Usage
    --------
    Initialize ExecutionPlan and add units
    >>> execution_plan = ExecutionPlan()
    >>> get_daily_profit = execution_plan.push(lambda: 1000)
    >>> get_daily_cost = execution_plan.push(lambda: 100)
    >>> get_daily_revenue = execution_plan.push(lambda profit, cost: profit - cost)
    >>> estimate_month_revenue = execution_plan.push(lambda daily_revenue: daily_revenue * 30)

    Interdependencies between execution units can be build incrementally

    >>> get_daily_revenue.require(get_daily_profit)
    >>> get_daily_revenue.require(get_daily_cost)
    >>> estimate_month_revenue.require(get_daily_revenue)

    Execution units in ExecutionPlan can be retrieved according to topological ordering:
    >>> execution_units = list(execution_plan.execution_units)
    >>> execution_units[-2] == get_daily_revenue
    True
    >>> execution_units[-1] == estimate_month_revenue
    True
    """

    EXECUTION_UNIT_FACTORY: ClassVar[
        Type[DependencyTrackingExecutionUnit]
    ] = DependencyTrackingExecutionUnit

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__()
        self._init_events()
        self._init_graph()

    def _init_events(self):
        self.on_requirements_satisfied = EventNotification()
        self.on_complete = EventNotification()

    def _init_graph(self) -> None:
        self.graph = nx.DiGraph()

    def _init_events_for_execution_unit(
        self, execution_unit: DependencyTrackingExecutionUnit
    ) -> None:
        # bind event listeners
        execution_unit.on_new_requirement.register(
            partial(self.__track_requirement, dependent=execution_unit)
        )
        execution_unit.on_requirements_satisfied.register(
            partial(self.on_requirements_satisfied, execution_unit)
        )
        execution_unit.on_complete.register(
            partial(self.on_complete, execution_unit=execution_unit)
        )

    @property
    def execution_units(self) -> Iterable[DependencyTrackingExecutionUnit]:
        """
        Returns a generator of execution units in topologically sorted order.
        """
        try:
            return nx.topological_sort(self.graph)
        except nx.NetworkXUnfeasible:
            return self.graph.nodes()

    def __iter__(self):
        yield from self.execution_units

    def __add__(self, other: Any) -> ExecutionPlan:
        if callable(other) or isinstance(other, DependencyTrackingExecutionUnit):
            self.push(other)
            return self
        else:
            raise TypeError("Expecting callable for right operand of add")

    def __iadd__(self, other: Any) -> ExecutionPlan:
        return self.__add__(other)

    def __track_requirement(
        self,
        prerequisite: DependencyTrackingExecutionUnit,
        dependent: DependencyTrackingExecutionUnit,
    ):
        self.graph.add_edge(prerequisite, dependent)

    def push(
        self, _callable: Union[Callable, DependencyTrackingExecutionUnit]
    ) -> DependencyTrackingExecutionUnit:
        execution_unit = (
            _callable
            if isinstance(_callable, DependencyTrackingExecutionUnit)
            else self.EXECUTION_UNIT_FACTORY(_callable)
        )
        self._init_events_for_execution_unit(execution_unit)

        self.graph.add_node(execution_unit)

        return execution_unit


if __name__ == "__main__":
    import doctest

    doctest.testmod()
