import asyncio
from unittest.mock import Mock

import pytest

from streamlined.ray.execution.execution_plan import (
    DependencyRequirements,
    DependencyTrackingRayExecutionUnit,
)


def test_dependency_requirements_on_new_requirement():
    mock = Mock()

    todos = DependencyRequirements()
    todos.on_new_requirement += mock

    todos["buy milk"] = False
    mock.assert_called_once_with(prerequisite="buy milk")

    todos["buy rice"] = False
    mock.assert_called_with(prerequisite="buy rice")


def test_dependency_requirements_on_all_requirements_satisfied():
    mock = Mock()

    todos = DependencyRequirements()
    todos.on_all_requirements_satisfied += mock

    todos["buy milk"] = False

    assert mock.call_count == 0
    todos["buy milk"] = True
    mock.assert_called_once_with()


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
