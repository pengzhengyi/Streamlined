from unittest.mock import Mock

import pytest

from streamlined.common import TYPE, VALUE
from streamlined.middlewares import (
    ARGPARSE,
    ARGS,
    ARGTYPE,
    ARGUMENTS,
    HELP,
    NAME,
    RUNSTAGES,
    RUNSTEPS,
    Context,
    Pipeline,
)


@pytest.mark.asyncio
async def test_pipeline_simple(simple_executor):
    context, scoping = Context.new(simple_executor)
    mock = Mock()

    def add(a, b):
        mock(a, b)
        return a + b

    pipeline = Pipeline(
        {
            NAME: "perform add of two numbers",
            ARGUMENTS: [{NAME: "a", VALUE: 10}, {NAME: "b", VALUE: 20}],
            RUNSTAGES: [{RUNSTEPS: [add]}],
        }
    )

    scoped = await pipeline.apply_into(context)
    mock.assert_called_once_with(10, 20)


@pytest.mark.asyncio
async def test_pipeline_print_help(simple_executor):
    pipeline = Pipeline(
        {
            ARGUMENTS: [
                {
                    NAME: "num_processors",
                    VALUE: {
                        TYPE: ARGPARSE,
                        NAME: "-p",
                        ARGTYPE: int,
                        ARGS: ["-p", "10"],
                        HELP: "specify the number of processors",
                    },
                }
            ],
        },
    )
    helpstr = pipeline.format_help()
    assert "specify the number of processors" in helpstr
