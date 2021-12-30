from __future__ import annotations

import logging
from logging.handlers import BufferingHandler

import nest_asyncio
import pytest
from faker import Faker

from streamlined.execution import SimpleExecutor

nest_asyncio.apply()


@pytest.fixture(scope="session")
def faker():
    return Faker()


@pytest.fixture
def buffering_handler():
    return BufferingHandler(10)


@pytest.fixture
def buffering_logger(faker, buffering_handler):
    logger = logging.getLogger(faker.uuid4())
    for handler in logger.handlers:
        logger.removeHandler(handler)

    logger.addHandler(buffering_handler)
    return logger


@pytest.fixture(scope="session")
def get_buffering_logger_message():
    return lambda logger, index: logger.handlers[0].buffer[index].msg


@pytest.fixture(scope="session")
def simple_executor():
    return SimpleExecutor()
