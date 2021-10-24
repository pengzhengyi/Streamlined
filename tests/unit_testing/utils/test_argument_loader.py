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


def test_parse_known_arguments():
    config, remaining_args = SimpleConfig.from_known_arguments(["FOO", "--bar", "BAR"])

    assert config.foo == "FOO"
    assert remaining_args == ["--bar", "BAR"]


@dataclass
class DatabaseConfig(ArgumentLoader):
    password: str = field(metadata={"name": ["-p"], "help": "supply password", "dest": "password"})
    database: InitVar[str] = field(
        metadata={"help": "supply value for database", "choices": ["mysql", "sqlite", "mongodb"]}
    )
    username: str = field(
        default="admin", metadata={"name": ["-u", "--username"], "help": "supply username"}
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
