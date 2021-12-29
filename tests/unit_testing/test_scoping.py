import pytest

from streamlined.services import Scoped, Scoping


def test_scoping_two_scopes():
    values = Scoping()
    values.global_scope["x"] = 1
    child_scope = values.create_scope(values.global_scope)
    child_scope["y"] = 10

    assert 11 == values.get("y", child_scope) + values.get("x", child_scope)

    with pytest.raises(KeyError):
        values.get("y", values.global_scope)


def test_nested_scope():
    activities = Scoping()
    day_activities = activities.create_scoped(parent_scope=activities.global_scope)
    night_activities = activities.create_scoped(parent_scope=activities.global_scope)

    activities.global_scope["free"] = 16

    day_activities["exercise"] = 2
    assert day_activities["free"] - day_activities["exercise"] == 14

    night_activities["sleep"] = 8
    assert night_activities["free"] - night_activities["sleep"] == 8

    activities.update(day_activities)
    activities.update(night_activities)
    assert activities.get("sleep", night_activities.current_scope) == 8


def test_scoping_update():
    scoping = Scoping()
    scoping.global_scope["Alice"] = "US"

    scoped = scoping.create_scoped(scoping.global_scope, Bob="UK")
    scoped["Jerry"] = "Germany"
    scoped.create_scope(Mary="France")

    scoping.update(scoped)

    assert len(list(scoping.all_scopes)) == 3
