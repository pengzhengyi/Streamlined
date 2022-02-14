import asyncio
import random
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock

import pytest

from streamlined import (
    ACTION,
    ARGUMENTS,
    CONCURRENCY,
    NAME,
    PARALLEL,
    RUNSTEP,
    RUNSTEPS,
    SCHEDULING,
    SUBSTEPS,
    SUPPRESS,
    VALUE,
    Runstep,
    Runsteps,
)
from streamlined.middlewares.runstep import SUBSTEPS


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

    scoped = await runstep.run(simple_executor)
    mock.assert_called_once_with(10, 20)
    assert scoped.getmagic(VALUE) == 30


@pytest.mark.asyncio
async def test_runstep_substeps(simple_executor):
    mock1 = Mock()
    mock2 = Mock()
    runstep = Runstep({ACTION: mock1, SUBSTEPS: [{ACTION: mock2}]})

    scoped = await runstep.run(simple_executor)
    mock1.assert_called_once()
    mock2.assert_called_once()


@pytest.mark.asyncio
async def test_runstep_suppress_no_argument_exception(simple_executor) -> None:
    suppressed_action = AsyncMock()

    def add(a, b):
        return a + b

    runstep = Runstep(
        {
            NAME: "perform add of two numbers",
            ACTION: add,
            SUPPRESS: {ACTION: suppressed_action},
        }
    )

    scoped = await runstep.run(simple_executor)
    suppressed_action.assert_awaited_once()


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


@pytest.mark.asyncio
async def test_runstep_parallel_with_max_concurrency(simple_executor):

    mock = Mock()

    async def sleep_and_do():
        asyncio.sleep(0.1)
        mock()
        return random.random()

    NUM_RUNSTEPS = 10

    def create_runsteps() -> List[Dict[str, Any]]:
        return [
            {
                RUNSTEP: {
                    ACTION: sleep_and_do,
                }
            }
            for i in range(NUM_RUNSTEPS)
        ]

    runstep = Runsteps({RUNSTEPS: {VALUE: create_runsteps, CONCURRENCY: 5}})

    scoped = await runstep.run(simple_executor)
    assert mock.call_count == NUM_RUNSTEPS
