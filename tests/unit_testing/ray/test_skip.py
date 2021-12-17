from unittest.mock import AsyncMock

import pytest

from streamlined.ray.common import ACTION, VALUE
from streamlined.ray.middlewares import SKIP, Skip


@pytest.mark.asyncio
async def test_skip_when_none_is_specified(simple_executor):
    skip = Skip(dict())
    should_skip = await skip.should_skip(simple_executor)
    assert should_skip is False


@pytest.mark.asyncio
async def test_skip_when_custom_action_is_run(simple_executor):
    custom_action = AsyncMock()
    original_action = AsyncMock()
    skip = Skip({SKIP: {VALUE: True, ACTION: custom_action}})
    await skip.apply(simple_executor, next=original_action)

    custom_action.assert_called_once()
    original_action.assert_not_called()
