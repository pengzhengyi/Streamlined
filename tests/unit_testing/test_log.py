import logging
from unittest.mock import Mock

import pytest

from streamlined.common import LEVEL, LOGGER, MESSAGE
from streamlined.middlewares import LOG, Log


@pytest.mark.asyncio
async def test_log_log_message(simple_executor):
    mock_logger = Mock()

    log = Log({LOG: {LEVEL: logging.WARNING, MESSAGE: "Hello World", LOGGER: mock_logger}})

    scoped = await log.run(simple_executor)

    mock_logger.assert_called_once()
