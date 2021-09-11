import pytest

from streamlined.component.proxies import MultithreadingCompliantManager


def test_multithreading_compliant_manager(minimum_manager):
    # values set in original manager
    minimum_manager.set_value("foo", "foo")
    assert minimum_manager.get_value("foo") == "foo"

    mc_manager = MultithreadingCompliantManager(manager=minimum_manager)
    # has same global scope
    mc_manager.get_global_scope() is minimum_manager.get_global_scope()

    # set bar='b' in mc manager

    mc_manager.set_value("bar", "b")
    assert mc_manager.get_value("bar") == "b"
    assert mc_manager.get_value("foo") == "foo"

    with pytest.raises(Exception):
        minimum_manager.get_value("bar")

    # set foo='f' in mc manager
    mc_manager.set_value("foo", "f")
    assert mc_manager.get_value("foo") == "f"
    assert minimum_manager.get_value("foo") == "foo"
