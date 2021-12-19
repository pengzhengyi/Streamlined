from __future__ import annotations

from dataclasses import dataclass, replace
from functools import partial
from typing import TYPE_CHECKING, Any, Awaitable, Coroutine, List, Optional, Tuple

from ..common import ASYNC_VOID
from ..services import EventNotification, Scoped, Scoping

if TYPE_CHECKING:
    from concurrent.futures import Executor


@dataclass
class MiddlewareContext:
    """
    Context for applying middleware.

    Attributes
    ------

    executor: An instance of [Executor](https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.Executor).
    Tasks can be submitted to this executor for async and parallel execution.
    next: Current execution chain. This is usually the `apply` of next middleware.
    scoped: The execution scope for this middleware. Should be returned
    as middleware's application result.
    """

    executor: Executor
    scoped: Scoped
    next: Coroutine[None, None, Optional[Scoped]] = ASYNC_VOID

    @classmethod
    def new(cls, executor: Executor) -> Tuple[MiddlewareContext, Scoping]:
        """
        Create a new middleware context from a executor.

        Scoped is created from a newly created Scoping.
        """
        scoping = Scoping()
        return (
            cls(
                executor=executor, scoped=scoping.create_scoped(parent_scope=scoping.global_scope)
            ),
            scoping,
        )


class Middleware:
    """
    A middleware should specify how it modifies the execution chain
    through the `apply` method.

    Events
    ------
    `before_apply`: emitted before applying the middleware to execution.
    Will receive this middleware and middleware context as argument
    `after_apply`: emitted after applying the middleware. Will receive the
    this middleware, middleware context, and `apply` invocation result,
    which should be the modified scope.
    """

    def __init__(self) -> None:
        super().__init__()
        self._init_events()

    def _init_events(self) -> None:
        self.before_apply = EventNotification()
        self.after_apply = EventNotification()

    @classmethod
    def get_name(cls):
        return cls.__name__.lower()

    async def _do_apply(self, context: MiddlewareContext) -> Awaitable[Scoped]:
        """
        Apply this middleware onto the execution chain.

        Should be overridden in subclasses to provide functionality.

        Returns
        ------
        Modified scope.

        * Return of modified scope is necessary in parallel execution scenario to
        * ensure the updates is captured.
        """
        return context.scoped

    async def apply(self, context: MiddlewareContext) -> Awaitable[Scoped]:
        """
        Apply this middleware onto the execution chain.

        Can be overridden in subclasses to provide some common code around middleware application.

        Parameters
        ------
        executor:
        next: Current execution chain. This is usually the result of `apply` of next middleware.
        """
        self.before_apply(middleware=self, context=context)
        scoped = await self._do_apply(context)
        self.after_apply(middleware=self, context=context, scoped=scoped)
        return scoped

    async def apply_to(self, context: MiddlewareContext) -> Awaitable[Scoped]:
        """
        Different from `apply` where middleware is committing the change to the scope,
        `apply_to` will add a scope to the existing scope in the context and make changes to it.

        Return
        ------
        The modified scope will be returned.
        """
        new_context = replace(context, scoped=context.scoped.create_scoped())
        scoped = await self.apply(new_context)

        if scoped is not None:
            context.scoped.update(scoped)
        return context.scoped


@dataclass
class _BoundMiddleware:
    middleware: Middleware
    context: MiddlewareContext

    async def apply(self) -> Awaitable[Scoped]:
        return await self.middleware.apply(self.context)

    async def apply_to(self) -> Awaitable[Scoped]:
        return await self.middleware.apply_to(self.context)


class Middlewares:
    """
    A queue of middleware.
    """

    middlewares: List[Middleware]

    def __init__(self) -> None:
        super().__init__()
        self.middlewares = []

    def apply(self, context: MiddlewareContext) -> Coroutine[None, None, Awaitable[Scoped]]:
        """
        Transform these middleware to a coroutine function.
        """
        if not self.middlewares:
            return context.next

        return self._apply(context, index=0)

    def _apply(
        self, context: MiddlewareContext, index: int = 0
    ) -> Coroutine[None, None, Awaitable[Scoped]]:
        if index == len(self.middlewares):
            return context.next

        # recursively apply for each middleware
        next = self._apply(context, index + 1)
        middleware = self.middlewares[index]

        middleware_context = replace(context, next=next)
        bound_middleware = _BoundMiddleware(middleware, middleware_context)

        return bound_middleware.apply_to
