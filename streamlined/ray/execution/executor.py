from __future__ import annotations

from concurrent.futures import Executor as AbstractExecutor
from concurrent.futures import Future
from dataclasses import dataclass, field
from typing import Any, AsyncIterable, Callable, Iterable, Mapping, Sequence, Union


@dataclass(frozen=True)
class Executable:
    """
    Capture function and arguments.
    """

    fn: Callable
    args: Sequence[Any] = field(default_factory=tuple)
    kwargs: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def of(cls, fn: Callable, *args: Any, **kwargs: Any):
        return cls(fn, args, kwargs)


class Executor(AbstractExecutor):
    """
    Executor is a class specialized at execution scheduling.

    The actual execution runs in provided `executor`.

    References:
    [concurrent.futures.Executor](https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.Executor).
    """

    executing: Mapping[Future, Executable]
    executed: Mapping[Future, Executable]

    def __init__(self, *args: Any, executor: AbstractExecutor, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.__init_executor(executor)

    def __init_executor(self, executor: AbstractExecutor):
        self.executor = executor
        self.executing = dict()
        self.executed = dict()

    def _on_complete(self, future: Future, executable: Executable) -> None:
        self.executing.pop(future, None)
        self.executed[future] = executable

    def submit(self, fn: Union[Callable, Executable], *args: Any, **kwargs: Any) -> Future:
        executable = fn if isinstance(fn, Executable) else Executable.of(fn, *args, **kwargs)

        future = self.executor.submit(executable.fn, *executable.args, **executable.kwargs)
        self.executing[future] = executable
        future.add_done_callback(lambda _future: self._on_complete(_future, executable))
        return future

    def map(self, executables: Iterable[Executable]) -> Iterable[Future]:
        for executable in executables:
            yield self.submit(executable)

    async def map_async(self, executables: AsyncIterable[Executable]) -> AsyncIterable[Future]:
        async for executable in executables:
            yield self.submit(executable)

    def shutdown(self, wait: bool, *args: Any, **kwargs: Any) -> None:
        return super().shutdown(wait, *args, **kwargs)


if __name__ == "__main__":
    import doctest

    doctest.testmod()
