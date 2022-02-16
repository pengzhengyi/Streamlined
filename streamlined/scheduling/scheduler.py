from math import ceil, inf
from typing import Callable, List, Optional, Union

from .schedule import Schedule
from .unit import Unit


class AbstractScheduler:
    """
    A scheduler can create a schedule from a list of execution units.
    """

    __slots__ = ()

    def __init__(self) -> None:
        pass

    def __call__(self, units: List[Unit]) -> Schedule:
        return self.create(units)

    def schedule(self, schedule: Schedule, units: List[Unit]) -> None:
        """
        Add execution units to a schedule.
        """
        raise NotImplementedError()

    def create(self, units: List[Unit]) -> Schedule:
        """Create a schedule from execution units."""
        schedule = Schedule()
        self.schedule(schedule, units)
        return schedule


class Sequential(AbstractScheduler):
    """
    Create a schedule from a list of execution units.

    In this schedule, these units will be executed sequentially:
    the second execution unit will start execution after the first
    execution unit finishes.
    """

    __slots__ = ()

    def schedule(self, schedule: Schedule, units: List[Unit]) -> None:
        last_unit: Optional[Unit] = None
        last_unit_index = len(units) - 1

        for i, unit in enumerate(units):
            is_first = i == 0
            is_last = i == last_unit_index

            schedule.push(unit, has_prerequisites=not is_first, has_dependents=not is_last)

            if last_unit is not None:
                unit.require(last_unit)

            last_unit = unit


class Parallel(Sequential):
    """
    Create a schedule from a list of execution units.

    In this schedule, at most a given number of units will be executed
    concurrently.

    For example, suppose `max_concurrency` is 2 and there are 5 execution
    units `A`, `B`, `C`, `D`, `E`. The created schedule will roughly looks
    like the following:

    ```
    SOURCE ──┬── A ──── B ──── C ──┬── SINK
             └── D ──── E ─────────┘
    ```
    """

    __slots__ = ("max_concurrency",)

    def __init__(self, max_concurrency: Union[int, float] = inf) -> None:
        """
        Create a Parallel scheduler.

        This scheduler by default support unlimited concurrency.
        """
        super().__init__()
        self.max_concurrency = max_concurrency

    def schedule(self, schedule: Schedule, units: List[Unit]) -> None:
        """
        Schedule a list of execution units as `max_concurrency` independent
        execution groups. In each execution group, execution units are
        executed sequentially.
        """
        num_units = len(units)
        groupsize = max(1, ceil(num_units / self.max_concurrency))
        for start in range(0, num_units, groupsize):
            units_in_group = units[start : start + groupsize]
            super().schedule(schedule, units_in_group)


Scheduler = Callable[[List[Unit]], Schedule]
SEQUENTIAL: Scheduler = Sequential()
PARALLEL: Scheduler = Parallel()
