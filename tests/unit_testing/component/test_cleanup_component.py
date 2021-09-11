import os

from streamlined import ACTION, ARGUMENTS, CLEANUP, NAME, VALUE
from streamlined.component import ExecutionComponent
from streamlined.component.argument_component import (
    ArgumentComponent,
    ArgumentsComponent,
)
from streamlined.component.cleanup_component import CleanupComponent
from streamlined.component.logging_component import LoggingComponent
from streamlined.component.runstep_component import RunstepComponent
from streamlined.component.validation_component import (
    ValidationAfterStageComponent,
    ValidatorComponent,
)


def test_runstep_component_for_a_add_b_and_log(minimum_manager, faker, tmpdir):
    tmpfile = os.path.join(tmpdir, "tmp.txt")

    config = {
        NAME: "add",
        ARGUMENTS: [
            {
                NAME: "tmpfile",
                VALUE: tmpfile,
            },
            {
                NAME: "writer",
                VALUE: lambda tmpfile: open(tmpfile, "w"),
            },
        ],
        ACTION: lambda writer: writer.write("a"),
        CLEANUP: lambda writer: writer.close(),
    }

    # Execution
    component = RunstepComponent.of(config)

    # Validation
    # one character is written
    assert component.execute(minimum_manager) == 1

    with open(tmpfile) as reader:
        assert reader.read() == "a"
