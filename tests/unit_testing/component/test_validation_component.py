from unittest.mock import Mock

from streamlined import ACTION, LEVEL, LOG, LOGGER, VALIDATION_AFTER_STAGE, VALUE
from streamlined.component.validation_component import (
    ValidationStageComponent,
    ValidatorComponent,
)


def test_minimum_validation_stage_component(
    minimum_manager, buffering_logger, get_buffering_logger_message
):
    # Setup
    mock = Mock(side_effect=[True, False])
    action = lambda: mock()
    log = {
        LEVEL: "ERROR",
        VALUE: lambda _validation_result_: str(_validation_result_),
        LOGGER: buffering_logger,
    }
    component = ValidationStageComponent(action, log)

    # First Execution: validation result is True
    component.execute(minimum_manager)
    mock.assert_called_once()
    assert get_buffering_logger_message(buffering_logger, 0) == str(True)

    # Second Execution: validation result is False
    component.execute(minimum_manager)
    assert get_buffering_logger_message(buffering_logger, 1) == str(False)


def test_validator_component_initialized_with_after_config(minimum_manager):
    mock = Mock(return_value=True)
    config = {
        VALIDATION_AFTER_STAGE: {
            ACTION: lambda: mock(),
            LOG: {LEVEL: "ERROR", VALUE: "Validation finished"},
        }
    }

    component = ValidatorComponent.of(config)

    for stage_validation_result in component.execute(minimum_manager):
        pass
    mock.assert_called_once()
