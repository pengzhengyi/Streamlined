from unittest.mock import AsyncMock

import pytest

from streamlined.ray.common import ACTION, HANDLERS, RETURN_TRUE
from streamlined.ray.middlewares import (
    VALIDATOR,
    VALIDATOR_AFTER_STAGE,
    VALIDATOR_BEFORE_STAGE,
    MiddlewareContext,
    Validator,
)


@pytest.mark.asyncio
async def test_validator_handler(simple_executor):
    true_handler_mock = AsyncMock()
    false_handler_mock = AsyncMock()
    validator = Validator(
        {
            VALIDATOR: {
                VALIDATOR_AFTER_STAGE: {
                    ACTION: RETURN_TRUE,
                    HANDLERS: {True: true_handler_mock, False: false_handler_mock},
                }
            }
        }
    )

    context, scoping = MiddlewareContext.new(simple_executor)
    await validator.apply(context)

    true_handler_mock.assert_awaited_once()
    false_handler_mock.assert_not_awaited()
