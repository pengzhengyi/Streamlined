from __future__ import annotations

from collections import OrderedDict, defaultdict
from typing import Any, Callable, ClassVar, Dict, Optional

from ..common import TAUTOLOGY_FACTORY, BidirectionalIndex
from ..services import DependencyTracking, EventNotification, Reaction, after, before


class NotifyNewRequirement(Reaction):
    def when(
        self,
        execution_requirements: ExecutionRequirements,
        prerequisite: DependencyTracking,
        is_satisfied: bool,
    ):
        return prerequisite not in execution_requirements

    def react(
        self,
        execution_requirements: ExecutionRequirements,
        prerequisite: DependencyTracking,
        is_satisfied: bool,
    ):
        execution_requirements.groups[execution_requirements.DEFAULT_GROUP] = prerequisite
        execution_requirements.on_new_requirement(prerequisite=prerequisite)


NOTIFY_NEW_REQUIREMENT = NotifyNewRequirement()


class NotifyRequirementsSatisfied(Reaction):
    def when(
        self,
        execution_requirements: ExecutionRequirements,
        prerequisite: DependencyTracking,
        *args: Any,
        **kwargs: Any,
    ):
        # since `is_satisfied` might be modified by condition, check directly
        if execution_requirements[prerequisite]:
            for group in execution_requirements.groups[prerequisite]:
                if execution_requirements.are_requirements_satisfied(group):
                    return True

        return False

    def react(
        self,
        execution_requirements: ExecutionRequirements,
        prerequisite: DependencyTracking,
        is_satisfied: bool,
        *args: Any,
        **kwargs: Any,
    ):
        execution_requirements.on_requirements_satisfied(prerequisite)


NOTIFY_REQUIREMENTS_SATISFIED = NotifyRequirementsSatisfied()


class ExecutionRequirements(OrderedDict):
    """
    ExecutionRequirements is used to model execution dependencies.

    Examples
    --------

    For example, in package manager like pip, a package `x` might require a package `y` installed with version at least `Vy` and a package `z` installed with version at least `Vz`.

    In other words, `y`, `z` are prerequisites for `x` with conditions like:

    y ─── version ≥ Vy ──┬── x
    z ─── version ≥ Vz ──┘

    This can be constructed as:
    ```
    reqs_for_x = ExecutionRequirements()
    reqs_for_x[y] = False
    reqs_for_x.conditions[y] = version > Vy
    reqs_for_x[z] = False
    reqs_for_x.conditions[z] = version > Vz
    ```

    This can become more complicated when there are different set of
    prerequisite that satisfy the requirements. For example, `x` can be
    installed when `α` has version at least `Vα`.

    y ─── version ≥ Vy ──┬── x
    z ─── version ≥ Vz ──┘   ║
    α ═══ version ≥ Vα ══════╝

    This introduces the concept of group. `y` and `z` becomes a requirement
    group and `α` becomes another requirement group. There is also a default
    requirement group containing every prerequisite. Since any non-default
    requirement group are subset of default requirement group, if the
    default requirement group is satisfied, at least one other non-default
    requirement group is also satisfied. In hypergraph's terminology, a
    group is the head set of a hyperedge.

    This can be constructed as:
    ```
    reqs_for_x.groups['group1'] = y
    reqs_for_x.groups['group1'] = z
    reqs_for_x.groups['group2'] = α
    ```

    Conditions
    --------
    Condition can be added for a prerequisite.

    When marking a prerequisite as satisfied, the condition is evaluated.
    Only if it evaluates to True will the prerequisite be marked as  satisfied.

    Event Notification
    --------

    ExecutionRequirements will trigger two events

    + `on_new_requirement` will notify when a new prerequisite is added
    + `on_requirements_satisfied` when all prerequisites in a requirement
    group are satisfied.

    Since check for event notification happens when a prerequisite is marked
    as satisfied (set to True), it is possible to trigger
    `on_requirements_satisfied` more than once.

    For example, suppose `y` and `z` are satisfied,
    `on_requirements_satisfied` in `x` will be triggered. If `α` is
    satisfied later, `on_requirements_satisfied` in `x` will be triggered again.

    Also because of the same reason, `on_requirements_satisfied` is only triggered when there exists requirements.

    See Also
    --------
    [Hypergraph](https://en.wikipedia.org/wiki/Hypergraph)

    An example of ![a directed hypergraph](https://en.wikipedia.org/wiki/File:Directed_hypergraph_example.svg).
    """

    DEFAULT_GROUP: ClassVar[str] = "__DEFAULT__"

    conditions: Dict[DependencyTracking, Callable[[], bool]]
    groups: BidirectionalIndex

    def __init__(self):
        super().__init__()
        self.__init_events()
        self.conditions = defaultdict(TAUTOLOGY_FACTORY)
        self.groups = BidirectionalIndex()

    def __init_events(self):
        self.on_new_requirement = EventNotification()
        self.on_requirements_satisfied = EventNotification()

    def __getitem__(self, prerequisite: DependencyTracking) -> bool:
        return super().__getitem__(prerequisite)

    @NOTIFY_NEW_REQUIREMENT.bind(at=before)
    @NOTIFY_REQUIREMENTS_SATISFIED.bind(at=after)
    def __setitem__(self, prerequisite: DependencyTracking, is_satisfied: bool):
        if is_satisfied:
            is_satisfied = self.conditions[prerequisite]()

        super().__setitem__(prerequisite, is_satisfied)

    def are_requirements_satisfied(self, group: Optional[str] = None) -> bool:
        """
        Check whether all prerequisites are marked as satisfied for a certain group.

        When group is not specified, default group will include all prerequisite.
        """
        if group is None:
            group = self.DEFAULT_GROUP

        return all(self[prerequisite] for prerequisite in self.groups[group])
