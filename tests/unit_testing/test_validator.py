from unittest.mock import AsyncMock

import pytest

from streamlined.common import ACTION, HANDLERS, RETURN_TRUE
from streamlined.middlewares import VALIDATOR, VALIDATOR_AFTER_STAGE, Validator


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

    scoped = await validator.run(simple_executor)

    true_handler_mock.assert_awaited_once()
    false_handler_mock.assert_not_awaited()
