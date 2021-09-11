import logging

from streamlined.component import LoggingComponent


def test_minimum_logging_component(
    faker, buffering_logger, minimum_manager, get_buffering_logger_message
):
    # Execution
    value = faker.text()
    component = LoggingComponent(value=value, logger=buffering_logger, level=logging.ERROR)
    future = component.execute(minimum_manager)
    assert get_buffering_logger_message(buffering_logger, 0) == value
