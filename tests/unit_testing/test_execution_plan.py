import asyncio
from unittest.mock import Mock

import pytest

from streamlined.execution import DependencyTrackingRayExecutionUnit


@pytest.mark.asyncio
async def test_execution_schedule_asynchronous_execution():
    async def sleep_and_return():
        await asyncio.sleep(0.1)
        return 100

    execution_unit = DependencyTrackingRayExecutionUnit(sleep_and_return)

    mock = Mock()
    execution_unit.on_complete.register(mock)

    await execution_unit()
    # assert await execution_unit()
    mock.assert_called_once_with(100)
