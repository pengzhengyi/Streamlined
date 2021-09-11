from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Dict, List

from ..constants import RUNSTAGES, VALUE
from .argument_component import ArgumentsComponent
from .capabilities import Skippable, WithName, WithTag
from .cleanup_component import CleanupComponent
from .component import Component, combine, stack
from .execution_component import ExecutionComponent
from .logging_component import LoggingComponentCombineWrapper
from .proxies import MultithreadingCompliantManager, RunstepsComponentProxy
from .runstep_component import RunstepsComponent
from .validation_component import Validatable

if TYPE_CHECKING:
    from ..manager.manager import Manager
    from ..manager.service.scoping import Scope
    from .capabilities.name_capability import TName

TRunstages = List[Dict[str, Any]]


class RunstageComponent(
    WithName,
    WithTag,
    combine(
        ArgumentsComponent,
        RunstepsComponent,
        ExecutionComponent,
        LoggingComponentCombineWrapper,
        CleanupComponent,
    ),
    Validatable,
    Skippable,
    Component,
):
    """
    A component that represents a runstage.
    """

    VALUE_KEYNAME: ClassVar[str] = VALUE

    def __get_default_execution_component(self) -> ExecutionComponent[Any]:
        return ExecutionComponent(lambda _runsteps_: _runsteps_.run())

    def __get_execution_component(self) -> ExecutionComponent[Any]:
        try:
            return self._Combined__get_component_by_name(ExecutionComponent.KEY_NAME)
        except KeyError:
            return self.__get_default_execution_component()

    def __execute_for_action(self, manager: Manager) -> Any:
        execution_component = self.__get_execution_component()
        return execution_component.execute(manager)

    def __execute_for_runsteps(self, manager: Manager) -> RunstepsComponent:
        try:
            name = RunstepsComponent.KEY_NAME
            runsteps_component = self._Combined__get_component_by_name(name)
            proxy = RunstepsComponentProxy(runsteps_component, manager)
            manager.set_magic_value(name, value=proxy)
        except KeyError:
            # runsteps are not provided, execute action directly
            ...

    def __execute(self, manager: Manager, scope: Scope) -> Any:
        proxy_manager = MultithreadingCompliantManager(manager)
        self.__execute_for_runsteps(proxy_manager)
        result = self.__execute_for_action(proxy_manager)
        scope.set_magic_value(name=self.VALUE_KEYNAME, value=result)
        return result

    def execute(self, manager: Manager) -> Any:
        with manager.scoped() as scope:

            validation_executor = Validatable.execute(self, manager)

            # execute before stage validation
            next(validation_executor)

            # executor for combined components
            executor = super().execute(
                manager,
                order=[
                    ArgumentsComponent.KEY_NAME,
                    LoggingComponentCombineWrapper.KEY_NAME,
                    CleanupComponent.KEY_NAME,
                ],
            )

            # Run arguments binding
            next(executor)

            # Run name binding
            self._execute_for_name(manager)

            # Run action
            result = self.__execute(manager, scope)

            # execute after stage validation
            next(validation_executor)

            # run logging
            next(executor)

            # run cleanup
            next(executor)

        # record result
        manager.set_result(self, result)
        return result


TRunstages = List[Dict[str, Any]]


class RunstagesComponent(stack(RunstageComponent)):
    """
    A component represents a series of runstage.

    Runstage are specified linearly in that later runstage will be executed after earlier runstage.
    """

    KEY_NAME: ClassVar[str] = RUNSTAGES

    def __init__(self, runstages: TRunstages, **kwargs: Any):
        super().__init__(configs=runstages, **kwargs)
