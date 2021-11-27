from __future__ import annotations

from asyncio import Queue as AsyncQueue
from contextlib import contextmanager
from multiprocessing import Queue
from typing import Any, AsyncIterable, Callable, ClassVar, Iterable, Optional

from ..common import VOID
from .execution_plan import DependencyTrackingExecutionUnit, ExecutionPlan


@contextmanager
def closing(thing: Any):
    try:
        yield thing
    finally:
        try:
            thing.close()
        except AttributeError:
            return


class ExecutionSchedule(ExecutionPlan):
    """
    Beyond what offers by ExecutionPlan (dependency tracking), ExecutionSchedule offers
    execution scheduling -- it can determine which execution units are ready to execute
    (based primarily on topology ordering) and take care of dependencies.
    """

    _ATTRIBUTE_NAME_FOR_SOURCE: ClassVar[str] = "source"
    _ATTRIBUTE_NAME_FOR_SINK: ClassVar[str] = "sink"

    @property
    def _source(self) -> DependencyTrackingExecutionUnit:
        return self.graph.graph[self._ATTRIBUTE_NAME_FOR_SOURCE]

    @property
    def _sink(self) -> DependencyTrackingExecutionUnit:
        return self.graph.graph[self._ATTRIBUTE_NAME_FOR_SINK]

    def __iter__(self) -> Iterable[DependencyTrackingExecutionUnit]:
        yield from self.walk()

    async def __aiter__(self) -> AsyncIterable[DependencyTrackingExecutionUnit]:
        async for execution_unit in self.walk_async():
            yield execution_unit

    def _init_events(self):
        super()._init_events()
        self.on_complete.register(self._notify_dependents)

    def _init_graph(self) -> None:
        super()._init_graph()
        self.__init_source_sink()

    def __init_source_sink(self) -> None:
        self.__init_terminal_node(self._ATTRIBUTE_NAME_FOR_SOURCE)
        self.__init_terminal_node(self._ATTRIBUTE_NAME_FOR_SINK)
        self._sink.require(self._source)

    def __add_requirement_for_source_sink(
        self, execution_unit: DependencyTrackingExecutionUnit
    ) -> None:
        execution_unit.require(self._source)
        self._sink.require(execution_unit)

    def __init_terminal_node(self, attribute_name: str) -> DependencyTrackingExecutionUnit:
        execution_unit = super().push(VOID)
        self.graph.graph[attribute_name] = execution_unit
        return execution_unit

    def _notify_dependents(
        self, result: Any, execution_unit: DependencyTrackingExecutionUnit
    ) -> None:
        for dependent in self.graph.successors(execution_unit):
            execution_unit.notify(dependent)

    def push(self, _callable: Callable):
        execution_unit = super().push(_callable)
        self.__add_requirement_for_source_sink(execution_unit)
        return execution_unit

    def walk(
        self,
        queue: Optional[Queue] = None,
        enqueue: Optional[Callable[[DependencyTrackingExecutionUnit], None]] = None,
        dequeue: Optional[Callable[..., DependencyTrackingExecutionUnit]] = None,
    ) -> Iterable[DependencyTrackingExecutionUnit]:
        """
        Yield the execution units as they can be executed (all prerequisites satisfied).

        The execution units will also be `enqueue` into `queue` when they become ready to execute.

        At each iteration, an execution unit will be dequeued from `queue` for actual execution.
        """
        if queue is None:
            queue = Queue()
        if enqueue is None:
            enqueue = queue.put
        if dequeue is None:
            dequeue = queue.get

        with closing(queue):
            with self.on_all_requirements_satisfied.registering(enqueue):
                self._source()

                while (execution_unit := dequeue()) != self._sink:
                    yield execution_unit

    async def walk_async(
        self,
        queue: Optional[Queue] = None,
        enqueue: Optional[Callable[[DependencyTrackingExecutionUnit], None]] = None,
        dequeue: Optional[Callable[..., DependencyTrackingExecutionUnit]] = None,
    ) -> AsyncIterable[DependencyTrackingExecutionUnit]:
        """
        Yield the execution units asynchronously as they can be executed.

        See Also
        --------
        `walk`
        """
        if queue is None:
            queue = AsyncQueue()
        if enqueue is None:
            enqueue = queue.put_nowait
        if dequeue is None:
            dequeue = queue.get

        with closing(queue):
            with self.on_complete.registering(lambda *args, **kwargs: queue.task_done()):
                with self.on_all_requirements_satisfied.registering(enqueue):
                    self._source()

                    while (execution_unit := await dequeue()) != self._sink:
                        yield execution_unit


if __name__ == "__main__":
    import doctest

    doctest.testmod()
