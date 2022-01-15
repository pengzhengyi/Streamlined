import asyncio
import random
from typing import Any, Dict, List
from unittest.mock import Mock

import pytest

from streamlined.common import VALUE
from streamlined.middlewares import (
    ACTION,
    NAME,
    PARALLEL,
    RUNSTEP,
    RUNSTEPS,
    SCHEDULING,
    Runstep,
    Runsteps,
)
from streamlined.middlewares.argument import ARGUMENTS


@pytest.mark.asyncio
async def test_runstep_action_requires_arguments(simple_executor):

    mock = Mock()

    def add(a, b):
        mock(a, b)
        return a + b

    runstep = Runstep(
        {
            RUNSTEP: {
                NAME: "perform add of two numbers",
                ARGUMENTS: [{NAME: "a", VALUE: 10}, {NAME: "b", VALUE: 20}],
                ACTION: add,
            }
        }
    )

    scoped = await runstep.run()
    mock.assert_called_once_with(10, 20)
    assert scoped.getmagic(VALUE) == 30


@pytest.mark.asyncio
async def test_runstep_parallel(simple_executor):

    mock = Mock()

    async def sleep_and_do():
        asyncio.sleep(0.1)
        mock()
        return random.random()

    NUM_RUNSTEPS = 50

    def create_runsteps() -> List[Dict[str, Any]]:
        return [
            {
                RUNSTEP: {
                    ACTION: sleep_and_do,
                }
            }
            for i in range(NUM_RUNSTEPS)
        ]

    runstep = Runsteps({RUNSTEPS: {VALUE: create_runsteps, SCHEDULING: PARALLEL}})

    scoped = await runstep.run(simple_executor)
    assert mock.call_count == NUM_RUNSTEPS
