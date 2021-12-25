from dataclasses import replace
from unittest.mock import AsyncMock

import pytest

from streamlined.ray.common import ACTION, VALUE
from streamlined.ray.middlewares import SKIP, Context, Skip


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
    context, _ = Context.new(simple_executor)
    context = replace(context, next=original_action)

    await skip.apply(context)

    custom_action.assert_awaited_once()
    original_action.assert_not_awaited()
