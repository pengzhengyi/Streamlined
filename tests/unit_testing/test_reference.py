from unittest.mock import Mock

import pytest

from streamlined import CLEANUP, NAME, VALUE, Argument, EvalRef, NameRef, ValueRef


@pytest.mark.asyncio
async def test_nameref_in_middleware(simple_executor):
    argument = Argument({NAME: NameRef("{origin}_dir"), VALUE: "/tmp"})
    scoping = await argument.run(simple_executor, origin="source")

    assert scoping.search("source_dir") == "/tmp"


@pytest.mark.asyncio
async def test_valueref_in_middleware(simple_executor):
    argument = Argument({NAME: NameRef("{origin}_dir"), VALUE: ValueRef("{origin}_dir")})
    scoping = await argument.run(simple_executor, origin="source", source_dir="/tmp")

    assert scoping.search("source_dir") == "/tmp"


def test_valueref_string_representation():
    ref = ValueRef("{origin}_dir")
    assert str(ref) == "{origin}_dir->?"
    directory = ref(dict(origin="source", source_dir="/tmp"))
    assert directory == "/tmp"
    assert str(ref) == "{origin}_dir|source_dir->/tmp"


def test_reference_overrides_and_fallbacks():
    ref = ValueRef(
        "{what}{which}", overrides=dict(what="tweet"), fallbacks=dict(which=1, tweet1="Hello")
    )
    tweet = ref(dict(which=100, tweet100="Welcome to the party!"))
    assert tweet == "Welcome to the party!"


@pytest.mark.asyncio
async def test_evalref(simple_executor):
    mock = Mock()

    def make_source_dir(source_dir: str) -> None:
        mock(source_dir)

    argument = Argument(
        {
            NAME: NameRef("{origin}_dir"),
            VALUE: ValueRef("{origin}_dir"),
            CLEANUP: EvalRef("make_{origin}_dir", overrides=dict(make_source_dir=make_source_dir)),
        }
    )
    scoped = await argument.run(simple_executor, origin="source", source_dir="/tmp")
    mock.assert_called_once_with("/tmp")
