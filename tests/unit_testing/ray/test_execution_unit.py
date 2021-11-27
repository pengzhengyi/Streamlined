import asyncio
from unittest.mock import Mock

import pytest

from streamlined.ray.execution import AsyncExecutionUnit, ExecutionStatus, ExecutionUnit


def test_execution_status():
    mock = Mock()
    execution_unit = ExecutionUnit(mock)

    assert execution_unit.status == ExecutionStatus.NotStarted
    execution_unit(1)

    mock.assert_called_once_with(1)
    assert execution_unit.status == ExecutionStatus.Completed


def test_on_complete_callable():
    mock = Mock()
    execution_unit = ExecutionUnit(mock)
    on_complete_mock = Mock()
    execution_unit.on_complete.register(on_complete_mock)

    execution_unit()
    on_complete_mock.assert_called_once()


@pytest.mark.asyncio
async def test_async_execution_unit():
    mock = Mock()
    execution_unit = AsyncExecutionUnit.empty()

    @AsyncExecutionUnit.bind(execution_unit=execution_unit)
    async def sleep_and_run():
        await asyncio.sleep(0.1)
        mock()

    await sleep_and_run()

    mock.assert_called_once()
    assert execution_unit.status == ExecutionStatus.Completed
