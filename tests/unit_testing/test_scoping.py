import os
from pathlib import Path

import pytest

from streamlined.services import Scoping, StoreScope
from streamlined.settings import SETTINGS


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


def test_scoped_update_for_different_global_scopes():
    scoping1 = Scoping()
    scoped1 = scoping1.create_scoped(scoping1.global_scope, Alice="US")

    scoping2 = Scoping()
    scoped2 = scoping2.create_scoped(scoping2.global_scope, Bob="UK")

    assert len(list(scoped1.all_scopes)) == 2
    scoped1.update(scoped2)

    assert len(list(scoped1.all_scopes)) == 4
    assert scoped1["Alice"] == "US"


def test_change():
    with Scoping() as scoping:
        scoping.global_scope["Alice"] = "US"

        scoped = scoping.create_scoped(scoping.global_scope, Bob="UK")
        scoped["Jerry"] = "Germany"

        scoped.change("Jerry", "UK")
        assert scoped["Jerry"] == "UK"

        with pytest.raises(KeyError):
            scoped.change("Benjamin", "France")


def test_store_at_file():
    with StoreScope() as scope:
        scope["shell"] = "bash"
        assert scope["shell"] == "bash"


def test_store_unpicklable():
    unpickleable = lambda: None
    with StoreScope() as scope:
        scope["unpickleable"] = unpickleable
        assert "unpickleable" in scope._memory


def test_to_dot(tmp_path: Path):
    filepath = tmp_path.joinpath("scoping.dot")
    assert not os.path.isfile(filepath)

    with Scoping() as scoping:
        scoping.global_scope["Alice"] = "US"
        scoping.write_dot(filepath)

    assert os.path.isfile(filepath)


def test_scope_with_settings(tmp_path: Path):
    SETTINGS.use_diskcache = True
    tmpdir = str(tmp_path)
    SETTINGS.tempdir = tmpdir

    assert len(os.listdir(tmpdir)) == 0

    with Scoping() as scoping:
        assert len(os.listdir(tmpdir)) != 0
