import os

from streamlined import (
    ACTION,
    ARGUMENTS,
    LOGGER,
    NAME,
    PATH,
    VALIDATION_AFTER_STAGE,
    VALIDATOR,
    VALUE,
)
from streamlined.component.logging_component import LoggingComponent
from streamlined.component.runstep_component import RunstepComponent


def test_runstep_component_for_1_add_1(minimum_manager):
    # Setup
    config = {NAME: "1+1", ACTION: lambda: 1 + 1}
    component = RunstepComponent.of(config)
    assert component.execute(minimum_manager) == 2


class MockLogger:
    def __init__(self, path):
        super().__init__()
        self.path = path

    def log(self, level, msg):
        self.path.write(msg)


def test_runstep_component_for_a_add_b_and_log(minimum_manager, faker, tmpdir):
    # setup
    filename = faker.file_name()
    p = tmpdir.join(filename)
    path = p.strpath
    logger = MockLogger(p)

    config = {
        NAME: "add",
        ACTION: lambda a, b: a + b,
        ARGUMENTS: [
            {
                NAME: "a",
                VALUE: 1,
            },
            {
                NAME: "b",
                VALUE: 2,
            },
        ],
        VALIDATOR: {
            VALIDATION_AFTER_STAGE: {
                ACTION: lambda: True,
                LoggingComponent.KEY_NAME: {
                    VALUE: lambda _value_: _value_,
                    LOGGER: logger,
                },
            }
        },
    }

    # Execution
    component = RunstepComponent.of(config)

    # Validation
    assert component.execute(minimum_manager) == 3
    assert p.read() == "3"
