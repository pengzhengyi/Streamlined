import argparse
from dataclasses import InitVar, dataclass, field
from typing import ClassVar

import pytest

from streamlined.utils import ArgumentLoader


@dataclass
class SimpleConfig(ArgumentLoader):
    foo: str


def test_simple_config():
    config: SimpleConfig = SimpleConfig.from_arguments(["FOO"])
    assert config.foo == "FOO"


@dataclass
class DatabaseConfig(ArgumentLoader):
    username: str = field(
        metadata={"name": ["-u", "--username"], "help": "supply username", "default": "admin"}
    )
    password: str = field(
        metadata={"name": ["-p"], "help": "supply value for j", "dest": "password"}
    )
    database: InitVar[str] = field(
        metadata={"help": "supply value for database", "choices": ["mysql", "sqlite", "mongodb"]}
    )

    def __post_init__(self, database):
        pass


def test_database_config():
    config: DatabaseConfig = DatabaseConfig.from_arguments(args=["mysql", "-p", "123456"])

    assert config.username == "admin"
    assert config.password == "123456"


def test_database_config_with_invalid_database_type():
    try:
        DatabaseConfig.from_arguments(args=["INVALID", "-p", "123456"])
    except SystemExit as e:
        assert isinstance(e.__context__, argparse.ArgumentError)
    else:
        raise ValueError("Exception not raised")