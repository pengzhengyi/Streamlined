from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Mapping, Optional, Tuple

from ..common import ASYNC_NOOP, ASYNC_VOID, MagicDict, ProxyDict
from ..execution import SimpleExecutor
from ..services import DependencyInjection, Scoped, Scoping

if TYPE_CHECKING:
    from concurrent.futures import Executor
ScopedNext = Callable[[], Awaitable[Optional[Scoped]]]


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
    next: ScopedNext = ASYNC_NOOP

    @property
    def magic_mappings(self) -> Mapping[str, Any]:
        mapping = MagicDict(
            executor=self.executor, scoped=self.scoped, next=self.next, context=self
        )
        return mapping

    @property
    def mappings(self) -> Mapping[str, Any]:
        return ProxyDict(self.scoped, self.magic_mappings)

    @classmethod
    def new(
        cls,
        executor: Optional[Executor] = None,
    ) -> Tuple[Context, Scoping]:
        """
        Create a new middleware context from a executor.

        When no executor is provided, default to create a `SimpleExecutor`.

        Scoped is created from a newly created Scoping.
        """
        if executor is None:
            executor = SimpleExecutor()

        scoping = Scoping()
        return (
            cls(
                executor=executor, scoped=scoping.create_scoped(parent_scope=scoping.global_scope)
            ),
            scoping,
        )

    def __getitem__(self, key: str) -> Any:
        return self.mappings[key]

    def __setitem__(self, key: str, item: Any) -> None:
        raise NotImplementedError("context provides a read-only view")

    async def submit(self, _callable: Callable[..., Any]) -> Any:
        bound_arguments = DependencyInjection.inject_callable(_callable, self.mappings)
        prepared_action = DependencyInjection.bind_callable(_callable, bound_arguments)

        result = await self.executor.submit(prepared_action)

        # write back key, value manually as value might be mutated
        for key, value in bound_arguments.arguments.items():
            with suppress(KeyError):
                self.scoped.change(key, value)

        if isinstance(result, Scoping):
            self.scoped.update(result)

        return result

    def update_scoped(self, scoped: Optional[Scoped]) -> Scoped:
        """
        Update with another scoped. Updated scoped will be returned.
        """
        if scoped is not None:
            self.scoped.update(scoped)
        return self.scoped

    def replace_with_void_next(self) -> Context:
        """
        Use a no-op function to replace current context's next
        function and return the new context.

        Current context will not be modified.
        """
        return replace(self, next=ASYNC_VOID)
