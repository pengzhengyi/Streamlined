from dataclasses import replace
from unittest.mock import AsyncMock

import pytest

from streamlined.ray.common import ACTION, VALUE
from streamlined.ray.middlewares import SKIP, Context, Skip


@pytest.mark.asyncio
async def test_skip_when_value_omitted(simple_executor):
    original_action = AsyncMock()
    skip = Skip({SKIP: {ACTION: original_action}})

    context, _ = Context.new(simple_executor)
    context = replace(context, next=original_action)
    await skip.apply_into(context)

    original_action.assert_awaited_once()


@pytest.mark.asyncio
async def test_skip_when_custom_action_is_run(simple_executor):
    custom_action = AsyncMock()
    original_action = AsyncMock()
    skip = Skip({SKIP: {VALUE: True, ACTION: custom_action}})
    context, _ = Context.new(simple_executor)
    context = replace(context, next=original_action)

    await skip.apply_into(context)

    custom_action.assert_awaited_once()
    original_action.assert_not_awaited()
