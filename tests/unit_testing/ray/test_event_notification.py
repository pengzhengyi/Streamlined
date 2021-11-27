from unittest.mock import Mock

from streamlined.ray.services import EventNotification


def test_unregister():
    mock = Mock()

    event = EventNotification()
    event += mock

    event(1)
    mock.assert_called_once_with(1)

    # unregister
    event -= mock
    event(2)
    mock.assert_called_once()
