from __future__ import annotations

from concurrent.futures import Executor, ProcessPoolExecutor, ThreadPoolExecutor, wait
from typing import Any, Callable, Iterable, Optional, Type, TypeVar, Union

import ray

T = TypeVar("T")


def remote(action: Any, *args: Any, **kwargs: Any) -> ray.ObjectRef:
    """
    Execute an action asynchronously with given arguments.

    If the action is already a `ray.RemoteFunction`, remote will be called with provided arguments.

    Otherwise, it will be transformed to `ray.RemoteFunction` first.

    An `ray.ObjectRef` will be returned. `ray.get` can be called to retrieve its result.
    """

    def decorator(func: Callable[..., Any]):
        @ray.remote
        def wrapper(*args: Any, **kwargs: Any):
            return func(*args, **kwargs)

        return wrapper.remote

    return getattr(action, "remote", decorator(action))(*args, **kwargs)


def parallel_map(
    func: Callable[..., T],
    *iterables: Iterable[Any],
    timeout: Optional[Union[int, float]] = None,
    chunksize: int = 1,
    executor: Type[Executor],
    **executor_args: Any
) -> Iterable[T]:
    """
    Initialize a [ThreadPoolExecutor](https://docs.python.org/3/library/concurrent.futures.html#threadpoolexecutor) using `executor_args` and run its map function.
    """
    with executor(**executor_args) as executor:
        return executor.map(func, *iterables, timeout=timeout, chunksize=chunksize)


def threading_map(
    func: Callable[..., T],
    *iterables: Iterable[Any],
    timeout: Optional[Union[int, float]] = None,
    chunksize: int = 1,
    **executor_args: Any
) -> Iterable[T]:
    """
    Initialize a [ThreadPoolExecutor](https://docs.python.org/3/library/concurrent.futures.html#threadpoolexecutor) using `executor_args` and run its map function.
    """
    return parallel_map(
        func,
        *iterables,
        timeout=timeout,
        chunksize=chunksize,
        executor=ThreadPoolExecutor,
        **executor_args
    )


def multiprocessing_map(
    func: Callable[..., T],
    *iterables: Iterable[Any],
    timeout: Optional[Union[int, float]] = None,
    chunksize: int = 1,
    **executor_args: Any
) -> Iterable[T]:
    """
    Initialize a [ProcessPoolExecutor](https://docs.python.org/3/library/concurrent.futures.html#processpoolexecutor) using `executor_args` and run its map function.
    """
    return parallel_map(
        func,
        *iterables,
        timeout=timeout,
        chunksize=chunksize,
        executor=ProcessPoolExecutor,
        **executor_args
    )
