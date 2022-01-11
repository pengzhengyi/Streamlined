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
    STDIN,
    STDOUT,
    Action,
    Context,
)


@pytest.mark.asyncio
async def test_action_execute_shell_command(simple_executor):
    context, _ = Context.new(simple_executor)

    action = Action({ACTION: {TYPE: SHELL, STDOUT: PIPE, ARGS: ["echo", "Hi"]}})

    scoped = await action.apply_into(context)

    result = scoped.getmagic(VALUE)
    assert result.stdout.strip() == b"Hi"


@pytest.mark.asyncio
async def test_action_argparse(simple_executor):
    context, _ = Context.new(simple_executor)

    action = Action(
        {ACTION: {TYPE: ARGPARSE, NAME: "--foo", ARGTYPE: int, ARGS: ["--foo", "1", "BAR"]}}
    )

    scoped = await action.apply_into(context)

    result = scoped.getmagic(VALUE)
    assert result == 1
