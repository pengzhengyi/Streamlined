from streamlined.common import format_help


def test_format_help():
    argument_definition = {"name": "square", "help": "display a square of a given number"}
    helpstr = format_help({"prog": "calculate"}, [argument_definition])

    assert argument_definition["help"] in helpstr
