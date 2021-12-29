import os

from streamlined import ACTION, ARGUMENTS, CLEANUP, NAME, VALUE
from streamlined.component.runstep_component import RunstepComponent


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
