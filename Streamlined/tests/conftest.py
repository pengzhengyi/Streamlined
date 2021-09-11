from __future__ import annotations

import logging
from logging.handlers import BufferingHandler

import pytest
from faker import Faker

from streamlined.manager import (
    ExecutionWithDependencyInjection,
    Logging,
    NameTracking,
    ResultCollection,
    Scoping,
    TagGrouping,
)
from streamlined.manager.manager import create_manager


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


@pytest.fixture
def minimum_manager():
    services = [
        NameTracking,
        ResultCollection,
        ExecutionWithDependencyInjection,
        Scoping,
        Logging,
        TagGrouping,
    ]
    return create_manager(*services)()


@pytest.fixture(scope="session")
def get_buffering_logger_message():
    return lambda logger, index: logger.handlers[0].buffer[index].msg
