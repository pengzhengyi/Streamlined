from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from ..constants import PIPELINE, VALUE
from .argument_component import ArgumentsComponent
from .capabilities import Skippable, WithName, WithTag
from .cleanup_component import CleanupComponent
from .component import Component, combine
from .runstage_component import RunstagesComponent
from .validation_component import Validatable

if TYPE_CHECKING:
    from ..manager.manager import Manager
    from ..manager.service.scoping import Scope
    from .capabilities.name_capability import TName


class PipelineComponent(
    WithName,
    WithTag,
    combine(ArgumentsComponent, RunstagesComponent, CleanupComponent),
    Validatable,
    Skippable,
    Component,
):
    """
    A component that represents a complete pipeline.
    """

    VALUE_KEYNAME: ClassVar[str] = VALUE
    KEY_NAME: ClassVar[str] = PIPELINE

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

            # Run runstages
            result = next(executor)
            scope.set_magic_value(name=self.VALUE_KEYNAME, value=result)

            # execute after stage validation
            next(validation_executor)

            # run cleanup
            next(executor)

        # record result
        manager.set_result(self, result)
        return result
