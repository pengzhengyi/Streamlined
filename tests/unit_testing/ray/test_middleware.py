from unittest.mock import AsyncMock

import pytest

from streamlined.ray.middlewares import (
    ACTION,
    CLEANUP,
    SKIP,
    Action,
    Cleanup,
    Context,
    Middlewares,
    Skip,
)


@pytest.mark.asyncio
async def test_middlewares_apply(simple_executor):
    act = AsyncMock()
    clean = AsyncMock()

    skip = Skip({SKIP: False})
    action = Action({ACTION: act})
    cleanup = Cleanup({CLEANUP: clean})

    middleware_queue = Middlewares()
    middleware_queue.middlewares.extend([skip, action, cleanup])

    act.assert_not_awaited()
    clean.assert_not_awaited()

    context, _ = Context.new(simple_executor)
    coroutine = middleware_queue.apply(context)

    await coroutine()
    act.assert_awaited_once()
    clean.assert_awaited_once()
