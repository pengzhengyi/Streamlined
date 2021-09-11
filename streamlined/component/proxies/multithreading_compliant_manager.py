from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Type

from .patch import patch

if TYPE_CHECKING:
    from ...manager.manager import Manager


class MultithreadingCompliantManagerPatch:
    def __init__(self, manager: Manager, **kwargs: Any):
        super().__init__(**kwargs)
        self._set_fake_head(manager)

    def _set_fake_head(self, manager: Manager) -> None:
        # add a new node and overshadow original _head
        self._head = manager._add_new_scope()


MultithreadingCompliantManager: Callable[Manager, Type[Manager]] = lambda manager: patch(
    proxy_target=manager,
    patch_provider=MultithreadingCompliantManagerPatch,
    manager=manager,
)
