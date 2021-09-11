from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, ClassVar, Union

from ...constants import NAME
from ..execution_component import ExecutionComponent
from .capability import Capability

if TYPE_CHECKING:
    from ...manager.manager import Manager


TName = Union[str, Callable[..., str]]


class WithName(Capability):
    """
    A mixin that allows a component to be named.
    """

    NAME_KEYNAME: ClassVar[str] = NAME

    def __init__(self, name: TName, **kwargs: Any):
        super().__init__(**kwargs)
        self.__set_name(name)

    def __set_name(self, name: TName) -> None:
        if isinstance(name, str):
            self._name = name
            self._name_getter = None
        else:
            self._name = None
            self._name_getter = ExecutionComponent(action=name)

    def __resolve_name(self, manager: Manager) -> str:
        if self._name is not None:
            return self._name

        return self._name_getter.execute(manager)

    def _register_name(self, name: str, manager: Manager) -> None:
        manager.set_name(name=name, component=self)
        manager.set_magic_value(name=self.NAME_KEYNAME, value=name)

    def _execute_for_name(self, manager: Manager) -> str:
        name = self.__resolve_name(manager)
        self._register_name(name, manager)
        return name
