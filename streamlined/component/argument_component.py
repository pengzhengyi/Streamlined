from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Union

from ..constants import ARGUMENTS, VALUE
from .capabilities import WithName
from .cleanup_component import CleanupComponent
from .component import Component, combine, stack
from .execution_component import ExecutionComponent
from .logging_component import LoggingComponentCombineWrapper
from .validation_component import Validatable

if TYPE_CHECKING:
    from ..manager.manager import Manager
    from ..manager.service.scoping import Scope
    from .capabilities.name_capability import TName

TArgument = Union[Dict[str, Any]]
TArguments = List[TArgument]


class ArgumentComponent(
    WithName, combine(LoggingComponentCombineWrapper, CleanupComponent), Validatable, Component
):
    """
    A component that binds an argument and its value to current scope.
    """

    VALUE_KEYNAME: ClassVar[str] = VALUE

    def __init__(self, value: Any, **kwargs: Any):
        super().__init__(**kwargs)
        self.__set_value(value)

    def __set_value(self, value: Any) -> None:
        if callable(value):
            self._value = None
            self._value_component = ExecutionComponent(value)
        else:
            self._value = value
            self._value_component = None

    def __resolve_value(self, manager: Manager) -> Any:
        if self._value is None:
            return self._value_component.execute(manager)
        else:
            return self._value

    def __execute_for_value(self, manager: Manager, scope: Scope) -> Any:
        value = self.__resolve_value(manager)
        scope.set_magic_value(name=self.VALUE_KEYNAME, value=value)
        return value

    def execute(self, manager: Manager) -> Any:
        prior_scope = manager.get_current_scope()
        with manager.scoped() as scope:
            name = self._execute_for_name(manager)
            validation_executor = Validatable.execute(self, manager)
            next(validation_executor)
            value = self.__execute_for_value(manager, scope)
            prior_scope.set_value(name, value)
            next(validation_executor)

            # executor for combined components
            executor = super().execute(manager)
            # run logging
            next(executor)

            # run cleanup
            next(executor)
            return value


class ArgumentsComponent(stack(ArgumentComponent)):
    KEY_NAME: ClassVar[str] = ARGUMENTS

    def __init__(self, arguments: TArguments, **kwargs: Any):
        super().__init__(configs=arguments, **kwargs)
