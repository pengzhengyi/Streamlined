from dataclasses import replace
from functools import partial
from typing import Any
from unittest.mock import AsyncMock

import pytest

from streamlined import ACTION, EXCEPTION, WHEN, Context, Suppress


def INDEX_EMPTY_DICT(key: Any) -> Any:
    return {}[key]


@pytest.mark.asyncio
async def test_skip_when_exception_is_suppressed(simple_executor):
    key = "foo"
    suppressed_action = AsyncMock()

    def key_in_error(exception: Exception) -> bool:
        return key in str(exception)

    skip = Suppress({ACTION: suppressed_action, EXCEPTION: KeyError, WHEN: key_in_error})

    context, _ = Context.new(simple_executor)
    context = replace(context, next=partial(INDEX_EMPTY_DICT, key))
    await skip.apply_into(context)

    suppressed_action.assert_awaited_once()
