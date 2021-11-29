from __future__ import annotations

import asyncio
from concurrent.futures import Executor as AbstractExecutor
from concurrent.futures import Future
from contextlib import ExitStack
from functools import partial
from typing import (
    Any,
    AsyncIterable,
    Callable,
    Dict,
    Iterable,
    Mapping,
    Optional,
    Union,
)

import ray
from ray.actor import ActorClass, ActorMethod
from ray.remote_function import RemoteFunction

from ..common import RayAsyncActor, RayRemote


class Executable:
    """
    Capture function and arguments.
    """

    def __init__(self, fn: Callable, *args: Any, **kwargs: Any):
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def __call__(self) -> Any:
        return self.fn(*self.args, **self.kwargs)


class Executor(AbstractExecutor):
    """
    Executor is a class specialized at execution scheduling.

    The actual execution runs in provided `executor`.

    References
    --------
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
        executable = fn if isinstance(fn, Executable) else Executable(fn, *args, **kwargs)

        future = self.executor.submit(executable.fn, *executable.args, **executable.kwargs)
        self.executing[future] = executable
        future.add_done_callback(partial(self._on_complete, executable=executable))
        return future

    def map(self, executables: Iterable[Executable]) -> Iterable[Future]:
        for executable in executables:
            yield self.submit(executable)

    async def map_async(self, executables: AsyncIterable[Executable]) -> AsyncIterable[Future]:
        async for executable in executables:
            yield self.submit(executable)

    def shutdown(self, wait: bool, *args: Any, **kwargs: Any) -> None:
        return super().shutdown(wait, *args, **kwargs)


class RayExecutor(AbstractExecutor):
    """
    Execute a task in Ray.
    """

    def __init__(self, *args: Any, should_shutdown_ray: bool = False, **kwargs):
        self._exit_stack = ExitStack()
        self.__init_ray_context(*args, should_shutdown_ray=should_shutdown_ray, **kwargs)

    def __init_ray_context(self, *args: Any, should_shutdown_ray: bool, **kwargs) -> None:
        if ray.is_initialized():
            self.ray_context = ray.get_runtime_context()
        else:
            self.ray_context = ray.init(*args, **kwargs)

        if hasattr(self.ray_context, "__exit__"):
            self._exit_stack.push(self.ray_context)
        elif should_shutdown_ray:
            self._exit_stack.callback(ray.shutdown)

    @staticmethod
    def _is_remote_function(fn: Any) -> bool:
        return isinstance(fn, RemoteFunction)

    @staticmethod
    def _is_actor_method(fn: Any) -> bool:
        return isinstance(fn, ActorMethod)

    @classmethod
    def _is_bound_actor_method(cls, fn: Any) -> bool:
        try:
            return cls._is_actor_method(fn.__self__)
        except AttributeError:
            return False

    @staticmethod
    def _is_actor(fn: Any) -> bool:
        return isinstance(fn, ActorClass)

    @classmethod
    def to_remote_function(
        cls,
        fn: Callable,
        ray_options: Optional[Dict[str, Any]] = None,
    ) -> ray.ObjectRef:
        if cls._is_bound_actor_method(fn):
            return fn
        elif cls._is_remote_function(fn) or cls._is_actor_method(fn):
            if ray_options:
                fn = fn.options(**ray_options)
            return fn.remote
        elif asyncio.iscoroutinefunction(fn):
            if ray_options:
                actor_constructor = RayAsyncActor.transform(**ray_options)
            else:
                actor_constructor = RayAsyncActor.transform

            actor = actor_constructor(fn)
            return actor.__call__.remote, actor
        else:
            if ray_options:
                return RayRemote(**ray_options)(fn)
            else:
                return RayRemote.transform(fn)

    @classmethod
    def run(cls, fn: Callable, *args, ray_options: Optional[Dict[str, Any]] = None, **kwargs):
        if asyncio.iscoroutinefunction(fn):
            remote_func, actor = cls.to_remote_function(fn, ray_options)
        else:
            remote_func = cls.to_remote_function(fn, ray_options)

        return remote_func(*args, **kwargs)

    def submit(self, fn: Callable, *args, ray_options: Optional[Dict[str, Any]] = None, **kwargs):
        return self.run(fn, *args, ray_options=ray_options, **kwargs)

    def map(self, func, *iterables, ray_options: Optional[Dict[str, Any]] = None):
        remote_func = self.to_remote_function(func, ray_options)
        for args in zip(*iterables):
            yield remote_func(*args)

    def shutdown(self, wait):
        return self._exit_stack.close()


if __name__ == "__main__":
    import doctest

    doctest.testmod()
