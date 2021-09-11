import logging
from unittest.mock import Mock

from streamlined import ACTION, LEVEL, LOG, LOGGER, NAME, RUNSTEPS, VALUE
from streamlined.component.runstage_component import RunstageComponent


def test_simple_runstage_component(minimum_manager):
    config = {
        NAME: "arithmetic",
        RUNSTEPS: [{NAME: "1+1", ACTION: lambda: 1 + 1}],
    }
    component = RunstageComponent.of(config)
    assert component.execute(minimum_manager) == [2]


def test_simple_runstage_component_with_logging(
    faker, buffering_logger, minimum_manager, get_buffering_logger_message
):
    value = faker.text()
    config = {
        NAME: "arithmetic",
        RUNSTEPS: [{NAME: "1+1", ACTION: lambda: 1 + 1}],
        LOG: {VALUE: value, LOGGER: buffering_logger, LEVEL: logging.ERROR},
    }
    component = RunstageComponent.of(config)
    component.execute(minimum_manager)

    # Result Validation
    assert get_buffering_logger_message(buffering_logger, 0) == value


def test_runstage_component_with_empty_runsteps(minimum_manager):
    config = {
        NAME: "arithmetic",
        ACTION: lambda: 1 + 2,
    }
    component = RunstageComponent.of(config)
    assert component.execute(minimum_manager) == 3


def test_runstage_component_multiple_runsteps_invocation(minimum_manager):
    increment_mock = Mock(side_effect=lambda value: value + 1)
    config = {
        NAME: "arithmetic",
        ACTION: lambda _runsteps_: [_runsteps_.run(n=n) for n in range(3)],
        RUNSTEPS: [
            {
                NAME: "1+1",
                ACTION: lambda n: increment_mock(n),
            }
        ],
    }
    component = RunstageComponent.of(config)
    component.execute(minimum_manager)
    assert increment_mock.call_args.args == (2,)
    assert increment_mock.call_count == 3
