from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Dict, List

from ..constants import RUNSTEPS, VALUE
from .argument_component import ArgumentsComponent
from .capabilities import Skippable, WithName, WithTag
from .cleanup_component import CleanupComponent
from .component import Component, combine, stack
from .execution_component import ExecutionComponent
from .logging_component import LoggingComponentCombineWrapper
from .validation_component import Validatable

if TYPE_CHECKING:
    from ..manager.manager import Manager
    from ..manager.service.scoping import Scope
    from .capabilities.name_capability import TName

TRunsteps = List[Dict[str, Any]]


class RunstepComponent(
    WithName,
    WithTag,
    combine(
        ArgumentsComponent,
        ExecutionComponent,
        LoggingComponentCombineWrapper,
        CleanupComponent,
    ),
    Validatable,
    Skippable,
    Component,
):
    """
    A component represents a runstep. A runstep will set up the environment before executing its action.
    """

    VALUE_KEYNAME: ClassVar[str] = VALUE

    def execute(self, manager: Manager) -> Any:
        with manager.scoped() as scope:
            validation_executor = Validatable.execute(self, manager)

            # execute before stage validation
            next(validation_executor)

            # executor for combined components
            executor = super().execute(manager)

            # Run arguments binding
            next(executor)

            # Run name binding
            self._execute_for_name(manager)

            # Run action
            result = next(executor)
            scope.set_magic_value(name=self.VALUE_KEYNAME, value=result)

            # execute after stage validation
            next(validation_executor)

            # run logging
            next(executor)

            # run cleanup
            next(executor)

        # record result
        manager.set_result(self, result)
        return result


class RunstepsComponent(stack(RunstepComponent)):
    """
    A component represents a series of runsteps.

    Runsteps are specified linearly in that later runstep will execute after earlier runstep.
    """

    KEY_NAME: ClassVar[str] = RUNSTEPS

    def __init__(self, runsteps: TRunsteps, **kwargs: Any):
        super().__init__(configs=runsteps, **kwargs)
