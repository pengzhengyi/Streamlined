from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, TypeVar

from .capability import Capability

if TYPE_CHECKING:
    from ...manager.manager import Manager

T = TypeVar("T")


class RunInNewScope(Capability):
    """
    A mixin that allows an action to be execute in a new scope with argument binding.
    """

    def __init__(self, manager: Manager, run_action: Callable[..., T], **kwargs: Any):
        self.__manager = manager
        self.__run_action = run_action
        super().__init__(**kwargs)

    def bindone(self, name: str, value: Any) -> Any:
        """
        Bind a argument.
        """
        self.__manager.set_value(name, value, self.__new_scope)
        return value

    def bind(self, **kwargs: Any) -> None:
        """
        Bind multiple arguments.
        """
        for name, value in kwargs.items():
            self.bindone(name, value)

    def run(self, **kwargs: Any) -> T:
        """
        Run designaed action in a new scope and bind specified arguments.
        """
        with self.__manager.scoped() as self.__new_scope:
            self.bind(**kwargs)
            result = self.__run_action()
        return result
