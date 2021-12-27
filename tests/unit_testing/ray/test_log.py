import contextlib
import io
import logging
import sys
from unittest.mock import Mock

import pytest

from streamlined.ray.common import LEVEL, LOGGER, MESSAGE
from streamlined.ray.middlewares import LOG, Context, Log


@pytest.mark.asyncio
async def test_log_log_message(simple_executor):
    mock_logger = Mock()

    log = Log({LOG: {LEVEL: logging.WARNING, MESSAGE: "Hello World", LOGGER: mock_logger}})

    context, scoping = Context.new(simple_executor)
    scoped = await log.apply_into(context)

    mock_logger.assert_called_once()
