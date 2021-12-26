from __future__ import annotations

import contextlib
import importlib
from dataclasses import dataclass, replace
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Coroutine,
    Dict,
    Iterable,
    List,
    Literal,
    Optional,
    Tuple,
    Type,
    Union,
)

from ..common import ASYNC_VOID, IS_NOT_LIST_OF_DICT
from ..services import DependencyInjection, EventNotification, Scoped, Scoping

if TYPE_CHECKING:
    from concurrent.futures import Executor


@dataclass
class Context:
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
    def new(cls, executor: Executor) -> Tuple[Context, Scoping]:
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

    async def submit(self, _callable: Callable) -> Any:
        prepared_action = DependencyInjection.prepare(_callable, self.scoped)
        return await self.executor.submit(prepared_action)

    def update_scoped(self, scoped: Scoped) -> Scoped:
        """
        Update with another scoped. Updated scoped will be returned.
        """
        if scoped is not None:
            self.scoped.update(scoped)
        return self.scoped


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

    @classmethod
    def get_name(cls) -> str:
        return cls.__name__.lower()

    async def _do_apply(self, context: Context) -> Awaitable[Scoped]:
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

    async def apply(self, context: Context) -> Awaitable[Scoped]:
        """
        Apply this middleware onto the execution chain.

        Can be overridden in subclasses to provide some common code around middleware application.

        Parameters
        ------
        executor:
        next: Current execution chain. This is usually the result of `apply` of next middleware.
        """
        scoped = await self._do_apply(context)
        return context.update_scoped(scoped)

    async def apply_to(self, context: Context) -> Awaitable[Scoped]:
        """
        Different from `apply` where middleware is committing the change to the scope,
        `apply_to` will add a scope to the existing scope in the context and make changes to it.

        Return
        ------
        The modified scope will be returned.
        """
        new_context = replace(context, scoped=context.scoped.create_scoped())
        return await self.apply(new_context)


@dataclass
class _BoundMiddleware:
    middleware: Middleware
    context: Context

    async def apply(self) -> Awaitable[Scoped]:
        return await self.middleware.apply(self.context)

    async def apply_to(self) -> Awaitable[Scoped]:
        return await self.middleware.apply_to(self.context)


class Middlewares:
    """
    A queue of middleware.
    """

    middlewares: List[Middleware]

    @classmethod
    def apply_middlewares(
        cls, context: Context, middlewares: Iterable[Middleware]
    ) -> Coroutine[None, None, Awaitable[Scoped]]:
        """
        Create a coroutine function where each middleware will be applied in order.
        """
        return cls._apply(context, middlewares, apply_method="apply")

    @classmethod
    def apply_middlewares_to(
        cls, context: Context, middlewares: Iterable[Middleware]
    ) -> Coroutine[None, None, Awaitable[Scoped]]:
        """
        Create a coroutine function where each middleware will be applied in order.

        Different from `apply`, the middlewares will be applied in new scope
        instead of existing scope.
        """
        return cls._apply(context, middlewares, apply_method="apply_to")

    @classmethod
    def _apply(
        cls,
        context: Context,
        middlewares: Iterable[Middlewares],
        apply_method: Union[Literal["apply"], Literal["apply_to"]] = "apply",
    ) -> Coroutine[None, None, Awaitable[Scoped]]:
        try:
            middleware = next(middlewares)
            context_next = cls._apply(context, middlewares, apply_method)

            middleware_context = replace(context, next=context_next)
            bound_middleware = _BoundMiddleware(middleware, middleware_context)

            return getattr(bound_middleware, apply_method)
        except StopIteration:
            return context.next

    def __init__(self) -> None:
        super().__init__()
        self.middlewares = []

    def get_middleware_by_type(self, middleware_type: Type[Middleware]) -> Middleware:
        """
        Get middleware by its type.
        """
        for middleware in self.middlewares:
            if isinstance(middleware, middleware_type):
                return middleware
        raise TypeError(f"No midleware has the specified type {middleware_type}")

    def get_middlewares_by_type(
        self, middleware_types: Iterable[Type[Middleware]]
    ) -> Iterable[Middleware]:
        """
        Get middlewares specified by their types.

        Existing middlewares will be yielded.
        """
        for middleware_type in middleware_types:
            with contextlib.suppress(TypeError):
                yield self.get_middleware_by_type(middleware_type)

    def apply(self, context: Context) -> Coroutine[None, None, Awaitable[Scoped]]:
        """
        Transform the registered middleware to a coroutine function.
        """
        return self.apply_middlewares(context, iter(self.middlewares))

    def apply_to(self, context: Context) -> Coroutine[None, None, Awaitable[Scoped]]:
        """
        Transform the registered middleware to a coroutine function.

        Different from `apply`, the middlewares will be applied in separate scope.
        """
        return self.apply_middlewares_to(context, iter(self.middlewares))


class WithMiddlewares(Middlewares):
    """
    A derived class of Middlewares that supports initialization of middlewares
    through their types.

    To use `WithMiddlewares`, derived class should implement `_init_middleware_types`
    with desired middleware types. Then call `create_middlewares_from` at appropriate place
    to initialize `self.middlewares`.
    """

    middleware_types: List[Type[Middleware]]

    def __init__(self) -> None:
        super().__init__()
        self._init_middleware_types()

    def _init_middleware_types(self):
        self.middleware_types = []

    def get_middleware_names(self) -> Iterable[str]:
        for middleware_type in self.middleware_types:
            yield middleware_type.get_name()

    def create_middlewares_from(self, value: Dict[str, Any]) -> Iterable[Middleware]:
        """
        Create middlewares using `value` if `value` is a dictionary and contains
        the middleware name.

        This assumes middleware config is keyed under middleware name.
        """
        for middleware_type, middleware_name in zip(
            self.middleware_types, self.get_middleware_names()
        ):
            if middleware_name in value:
                yield middleware_type(value)


class StackMiddleware(WithMiddlewares):
    """
    StackMiddleware means middleware of same type is stacked --
    multiple instances of this middleware type is initialized.

    The value to parse should be a list of dictionary where each
    dictionary is parseable by that middleware type.

    At its application, the initialized instances will be applied in list order.

    When `_init_stacked_middleware_type` is not overridden, the
    default typename will be current class name without ending 's'
    and type will be resolved dynamically by looking at class defined
    in same module name.
    """

    @classmethod
    def _get_default_stacked_middleware_name(cls) -> str:
        self_name = cls.__name__

        if self_name.endswith("s"):
            return self_name[:-1]

        raise ValueError("Cannot infer middleware name to stack")

    def __init__(self) -> None:
        self._init_stacked_middleware_type()
        super().__init__()

    def _init_stacked_middleware_type(self) -> None:
        self._stacked_middleware_typename = self._get_default_stacked_middleware_name()

        self._stacked_middleware_type = self._convert_middleware_typename_to_type(
            self._stacked_middleware_typename
        )

    def _convert_middleware_typename_to_type(self, name: str) -> Type[Middleware]:
        current_module_path = __name__
        parent_module_path = current_module_path[: current_module_path.rindex(".")]
        module = importlib.import_module(f".{name.lower()}", parent_module_path)
        return getattr(module, name)

    def _init_middleware_types(self):
        super()._init_middleware_types()
        self.middleware_types.append(self._stacked_middleware_type)

    def create_middlewares_from(self, value: Dict[str, Any]) -> Iterable[Middleware]:
        for middleware_type, middleware_name in zip(
            self.middleware_types, self.get_middleware_names()
        ):
            for argument_value in value:
                new_value = {middleware_name: argument_value}
                yield middleware_type(new_value)
