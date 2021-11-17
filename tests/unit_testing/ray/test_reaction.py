import pytest

from streamlined.ray.services import raises


def test_raises_return_default_value_at_expected_exception():
    def error_throwing_func():
        raise ValueError()

    with pytest.raises(ValueError):
        error_throwing_func()

    error_caught_func = raises(do=lambda *args, **kwargs: True, expected_exception=ValueError)(
        error_throwing_func
    )
    assert error_caught_func()
