from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Mapping, Optional, Tuple

from ..common import ASYNC_NOOP, ASYNC_VOID, MagicDict, ProxyDict
from ..execution import SimpleExecutor
from ..services import DependencyInjection, HybridStorageOption, Scoped, Scoping

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
        storage_option: HybridStorageOption = HybridStorageOption.TRANSIENT_MEMORY,
    ) -> Tuple[Context, Scoping]:
        """
        Create a new middleware context from a executor.

        When no executor is provided, default to create a `SimpleExecutor`.

        Scoped is created from a newly created Scoping.
        """
        if executor is None:
            executor = SimpleExecutor()

        scoping = Scoping.of(storage_option)
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

    def prepare(self, _callable: Callable[..., Any]) -> Callable[..., Any]:
        return DependencyInjection.prepare(_callable, self.mappings)

    async def submit(self, _callable: Callable[..., Any]) -> Any:
        prepared_action = self.prepare(_callable)
        result = await self.executor.submit(prepared_action)

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
