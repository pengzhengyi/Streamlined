import inspect
from unittest.mock import Mock

import pytest

from streamlined.ray.services import Reaction, after, before, raises


def test_raises_return_default_value_at_expected_exception():
    def error_throwing_func():
        raise ValueError()

    with pytest.raises(ValueError):
        error_throwing_func()

    error_caught_func = raises(do=lambda *args, **kwargs: True, expected_exception=ValueError)(
        error_throwing_func
    )
    assert error_caught_func()


def test_preserve_signature():
    def add(x: int, y: int) -> int:
        return x + y

    transformed_add = after()(before()(raises()(add)))
    assert inspect.signature(transformed_add) == inspect.signature(add)


def test_reaction():
    mock = Mock()

    class MockReaction(Reaction):
        def react(self, *args, **kwargs):
            mock(*args, **kwargs)

    reactor = MockReaction()

    @reactor.bind(at=before)
    def add(x, y):
        return x + y

    assert add(1, 2) == 3
    mock.assert_called_with(1, 2)

    assert add(10, 20) == 30
    mock.assert_called_with(10, 20)
