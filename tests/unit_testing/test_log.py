import logging
from unittest.mock import MagicMock, Mock

import pytest

from streamlined import (
    ARGUMENTS,
    LEVEL,
    LOG,
    LOGGER,
    MESSAGE,
    NAME,
    RUNSTAGE,
    RUNSTAGES,
    RUNSTEPS,
    VALUE,
    Log,
    Pipeline,
    to_magic_naming,
)


class MockLogger:
    def __init__(self) -> None:
        self.mock = MagicMock()

    def log(self, level: int, message: str) -> None:
        self.mock(level, message)


@pytest.mark.asyncio
async def test_log_log_message(simple_executor):
    mock_logger = Mock()

    log = Log({LOG: {LEVEL: logging.WARNING, MESSAGE: "Hello World", LOGGER: mock_logger}})

    scoped = await log.run(simple_executor)

    mock_logger.assert_called_once()


@pytest.mark.asyncio
async def test_nested_log(simple_executor):
    pipeline_logger = MockLogger()

    def add(a, b):
        return a + b

    pipeline = Pipeline(
        {
            NAME: "perform add of two numbers",
            ARGUMENTS: [
                {NAME: "a", VALUE: 10},
                {NAME: "b", VALUE: 20},
                {NAME: to_magic_naming(LOGGER), VALUE: pipeline_logger},
            ],
            RUNSTAGES: [{RUNSTAGE: {RUNSTEPS: [add], LOG: {MESSAGE: "RUNSTAGE LOG MESSAGE"}}}],
            LOG: {MESSAGE: "PIPELINE LOG MESSAGE"},
        }
    )

    scoped = await pipeline.run(simple_executor)

    assert pipeline_logger.mock.call_count == 2
