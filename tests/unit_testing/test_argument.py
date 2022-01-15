from unittest.mock import Mock

import pytest

from streamlined.common import TYPE, VALUE
from streamlined.middlewares import (
    ARGPARSE,
    ARGS,
    ARGTYPE,
    ARGUMENT,
    ARGUMENTS,
    CLEANUP,
    NAME,
    SKIP,
    Argument,
    Arguments,
)


@pytest.mark.asyncio
async def test_argument_set_in_scope(simple_executor):
    argument = Argument({ARGUMENT: {NAME: "first_name", VALUE: "Alice"}})
    scoped = await argument.run(simple_executor)
    assert scoped["first_name"] == "Alice"


@pytest.mark.asyncio
async def test_argument_skip(simple_executor):

    argument = Argument({ARGUMENT: {NAME: "first_name", VALUE: "Alice", SKIP: True}})
    scoped = await argument.run(simple_executor)

    with pytest.raises(KeyError):
        scoped["first_name"]


@pytest.mark.asyncio
async def test_argument_set_after_action(simple_executor):
    mock = Mock()

    def is_name_set(name) -> str:
        mock(name)

    argument = Argument({ARGUMENT: {NAME: "name", VALUE: "Alice", CLEANUP: is_name_set}})
    scoped = await argument.run(simple_executor)

    mock.assert_called_once_with("Alice")


@pytest.mark.asyncio
async def test_argument_argparse(simple_executor):

    argument = Argument(
        {
            ARGUMENT: {
                NAME: "num_processors",
                VALUE: {TYPE: ARGPARSE, NAME: "-p", ARGTYPE: int, ARGS: ["-p", "10", "--help"]},
            }
        }
    )
    scoped = await argument.run(simple_executor)
    assert scoped.get("num_processors") == 10


@pytest.mark.asyncio
async def test_argument_argparse_parsed_argument_not_present(simple_executor):

    argument = Argument(
        {
            ARGUMENT: {
                NAME: "num_processors",
                VALUE: {TYPE: ARGPARSE, NAME: "-p", ARGTYPE: int, ARGS: ["--foo"]},
            }
        }
    )
    scoped = await argument.run(simple_executor)
    assert scoped.get("num_processors") is None


@pytest.mark.asyncio
async def test_arguments_set_in_scope(simple_executor):

    arguments = Arguments(
        {ARGUMENTS: [{NAME: "first_name", VALUE: "John"}, {NAME: "last_name", VALUE: "Doe"}]}
    )
    scoped = await arguments.run(simple_executor)
    assert scoped["first_name"] == "John"
    assert scoped["last_name"] == "Doe"
