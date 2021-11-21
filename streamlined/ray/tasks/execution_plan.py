from __future__ import annotations

from collections import OrderedDict
from typing import Any, Callable, ClassVar, Iterable, Optional, Type, Union

import networkx as nx

from ..common import VOID
from ..services import DependencyTracking as _DependencyTracking
from ..services import EventNotification, Reaction, after, before
from .execution_unit import ExecutionUnit as _ExecutionUnit


class NotifyNewRequirement(Reaction):
    def when(
        self,
        dependency_requirements: DependencyRequirements,
        prerequisite: _DependencyTracking,
        is_satisfied: bool,
    ):
        return prerequisite not in dependency_requirements

    def react(
        self,
        dependency_requirements: DependencyRequirements,
        prerequisite: _DependencyTracking,
        is_satisfied: bool,
    ):
        dependency_requirements.on_new_requirement(prerequisite=prerequisite)


NOTIFY_NEW_REQUIREMENT = NotifyNewRequirement()


class NotifyAllRequirementsSatisfied(Reaction):
    def when(
        self,
        dependency_requirements: DependencyRequirements,
        prerequisite: _DependencyTracking,
        is_satisfied: bool,
        *args: Any,
        **kwargs: Any,
    ):
        return is_satisfied and dependency_requirements.are_requirements_satisfied

    def react(
        self,
        dependency_requirements: DependencyRequirements,
        prerequisite: _DependencyTracking,
        is_satisfied: bool,
        *args: Any,
        **kwargs: Any,
    ):
        dependency_requirements.on_all_requirements_satisfied()


NOTIFY_ALL_REQUIREMENTS_SATISFIED = NotifyAllRequirementsSatisfied()


class DependencyRequirements(OrderedDict):
    """
    DependencyRequirements provides two important properties:

    - ordering
    - event notification when all prerequisites are satisfied

    !  Since check for event notification happens when a prerequisite is marked as satisfied (set to True), it is possible to trigger `on_all_requirements_satisfied` more than once. Due to the same reason, `on_all_requirements_satisfied` is only triggered when there exists requirements.
    """

    def __init__(self):
        super().__init__()
        self.__init_events()

    def __init_events(self):
        self.on_new_requirement = EventNotification()
        self.on_all_requirements_satisfied = EventNotification()

    def __getitem__(self, prerequisite: _DependencyTracking) -> bool:
        return super().__getitem__(prerequisite)

    @NOTIFY_NEW_REQUIREMENT.bind(at=before)
    @NOTIFY_ALL_REQUIREMENTS_SATISFIED.bind(at=after)
    def __setitem__(self, prerequisite: _DependencyTracking, is_satisfied: bool):
        super().__setitem__(prerequisite, is_satisfied)

    @property
    def are_requirements_satisfied(self) -> bool:
        return all(self.values())


class ExecutionUnit(_DependencyTracking, _ExecutionUnit):
    """
    Beyond plain `ExecutionUnit` and `DependencyTracking`, this provides EventNotification when all prerequisites are satisfied and when execution completed.
    """

    REQUIREMENTS_FACTORY: ClassVar[Type[DependencyRequirements]] = DependencyRequirements

    def __init__(self, _callable: Callable = VOID):
        super().__init__(_callable=_callable)

    @property
    def on_new_requirement(self) -> EventNotification:
        return self._requirements.on_new_requirement

    @property
    def on_all_requirements_satisfied(self) -> EventNotification:
        return self._requirements.on_all_requirements_satisfied


class ExecutionPlan:
    """
    ExecutionPlan can be seen as a Directed Acyclic Graph of ExecutionUnit. More specifically, nodes are callables while edges are dependency relationships.

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

    EXECUTION_UNIT_FACTORY: ClassVar[Type[ExecutionUnit]] = ExecutionUnit

    def __init__(self, *args: Any, graph: Optional[nx.DiGraph] = None, **kwargs: Any):
        super().__init__()
        self.__init_graph(graph)
        self.__init_events()

    def __init_events(self):
        self.on_all_requirements_satisfied = EventNotification()

    def __init_graph(self, graph: Optional[nx.DiGraph]) -> None:
        self.graph = graph if graph else nx.DiGraph()

    def _track_requirement(self, prerequisite: ExecutionUnit, dependent: ExecutionUnit):
        self.graph.add_edge(prerequisite, dependent)

    @property
    def execution_units(self) -> Iterable[ExecutionUnit]:
        """
        Returns a generator of execution units in topologically sorted order.
        """
        return nx.topological_sort(self.graph)

    def push(self, execution_unit: Union[Callable, ExecutionUnit]) -> ExecutionUnit:
        if not isinstance(execution_unit, ExecutionUnit):
            execution_unit = self.EXECUTION_UNIT_FACTORY(execution_unit)
        else:
            # track existing requirements
            for prerequisite in execution_unit.prerequisites:
                self._track_requirement(prerequisite, execution_unit)

        # bind event listeners
        execution_unit.on_new_requirement + (
            lambda prerequisite: self._track_requirement(prerequisite, execution_unit)
        )
        execution_unit.on_all_requirements_satisfied + (
            lambda: self.on_all_requirements_satisfied(execution_unit=execution_unit)
        )

        self.graph.add_node(execution_unit)

        return execution_unit


if __name__ == "__main__":
    import doctest

    doctest.testmod()
