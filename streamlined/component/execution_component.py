from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, ClassVar, Generic, TypeVar

from ..constants import ACTION
from .component import Component

if TYPE_CHECKING:
    from ..manager.manager import Manager


T = TypeVar("T")


class ExecutionComponent(Component, Generic[T]):
    """
    A component that executes a callable in current execution scope.
    """

    KEY_NAME: ClassVar[str] = ACTION

    def __init__(self, action: Callable[..., T], **kwargs: Any):
        super().__init__(**kwargs)
        self._action = action

    def __call__(self, *args: Any, **kwargs: Any) -> T:
        return self.execute(*args, **kwargs)

    def execute(self, manager: Manager) -> T:
        return manager.execute(self._action)
