from subprocess import PIPE

import pytest

from streamlined.common import TYPE, VALUE
from streamlined.middlewares import (
    ACTION,
    ARGPARSE,
    ARGS,
    ARGTYPE,
    NAME,
    SHELL,
    STDOUT,
    Action,
)


@pytest.mark.asyncio
async def test_action_execute_shell_command(simple_executor):
    action = Action({ACTION: {TYPE: SHELL, STDOUT: PIPE, ARGS: ["echo", "Hi"]}})

    scoping = await action.run(simple_executor)

    result = scoping.searchmagic(VALUE)
    assert result.stdout.strip() == b"Hi"


@pytest.mark.asyncio
async def test_action_argparse(simple_executor):
    action = Action(
        {ACTION: {TYPE: ARGPARSE, NAME: "--foo", ARGTYPE: int, ARGS: ["--foo", "1", "BAR"]}}
    )

    scoping = await action.run(simple_executor)

    result = scoping.searchmagic(VALUE)
    assert result == 1
