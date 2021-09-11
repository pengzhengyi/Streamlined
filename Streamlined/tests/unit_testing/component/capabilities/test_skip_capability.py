from unittest.mock import Mock

from streamlined import (
    ACTION,
    ARGUMENTS,
    LOGGER,
    NAME,
    PATH,
    SKIP,
    VALIDATION_AFTER_STAGE,
    VALIDATOR,
    VALUE,
)
from streamlined.component.logging_component import LoggingComponent
from streamlined.component.runstep_component import RunstepComponent


def test_nonskip_runstep_component_by_specifying_skip_to_false(minimum_manager):
    config = {NAME: "1+1", ACTION: lambda: 1 + 1, SKIP: False}
    component = RunstepComponent.of(config)
    assert component.execute(minimum_manager) == 2


def test_nonskip_runstep_component_by_not_specifying_skip(minimum_manager):
    config = {NAME: "1+1", ACTION: lambda: 1 + 1}
    component = RunstepComponent.of(config)
    assert component.execute(minimum_manager) == 2


def test_skip_runstep_component_by_specify_skip_to_true(minimum_manager):
    mock = Mock(side_effect=ValueError("Should not invoke"))
    config = {NAME: "1+1", ACTION: lambda: mock(), SKIP: True}
    component = RunstepComponent.of(config)
    mock.assert_not_called()


def test_skip_runstep_component_by_specify_skip_to_lambda_that_evaluates_to_true(
    minimum_manager,
):
    mock = Mock(side_effect=ValueError("Should not invoke"))
    config = {NAME: "1+1", ACTION: lambda: mock(), SKIP: lambda: True}
    component = RunstepComponent.of(config)
    mock.assert_not_called()


def test_skip_runstep_component_with_fallback_action(minimum_manager):
    config = {NAME: "1+1", ACTION: lambda: 1 + 1, SKIP: {VALUE: True, ACTION: lambda: 2 + 2}}
    component = RunstepComponent.of(config)
    assert component.execute(minimum_manager) == 4
