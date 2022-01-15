import asyncio
from typing import Awaitable, Callable, TypeVar

import pytest

from streamlined import rewrite_function_parameters

T = TypeVar("T")


@pytest.mark.asyncio
async def test_rewrite_async_function() -> None:
    hsleep: Callable[[float, T], Awaitable[T]] = rewrite_function_parameters(
        asyncio.sleep, "hsleep", "duration", result="wakeup_with"
    )
    assert asyncio.iscoroutinefunction(hsleep)
    result = await hsleep(0.1, "waked up")
    assert result == "waked up"
