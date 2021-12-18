from __future__ import annotations

from typing import TYPE_CHECKING, List

from ..common import ASYNC_VOID

if TYPE_CHECKING:
    from concurrent.futures import Executor


class Middleware:
    """
    A middleware should specify how it modifies the execution chain
    through the `apply` method.
    """

    @classmethod
    def get_name(cls):
        return cls.__name__.lower()

    async def apply(self, executor: Executor, next):
        """
        Apply this middleware onto the execution chain.

        Parameters
        ------
        executor: An instance of [Executor](https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.Executor).
        Tasks can be submitted to this executor for async and parallel execution.
        next: Current execution chain. This is usually the result of `apply` of next middleware.
        """
        raise NotImplementedError


class _BoundMiddleware:
    def __init__(self, middleware: Middleware, executor: Executor, next) -> None:
        self.middleware = middleware
        self.executor = executor
        self.next = next

    async def apply(self):
        return await self.middleware.apply(self.executor, self.next)


class Middlewares:
    """
    A queue of middleware.
    """

    middlewares: List[Middleware]

    def __init__(self) -> None:
        self.middlewares = []

    def apply(self, executor):
        """
        Transform these middleware to an async executable.
        """
        if not self.middlewares:
            return ASYNC_VOID

        return self._apply(executor, index=0)

    def _apply(self, executor, index: int = 0):
        if index == len(self.middlewares):
            return ASYNC_VOID

        # recursively apply for each middleware
        next = self._apply(executor, index + 1)
        current_middleware = _BoundMiddleware(self.middlewares[index], executor, next)
        return current_middleware.apply
