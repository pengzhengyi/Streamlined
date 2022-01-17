import pytest

from streamlined import NAME, VALUE, Argument, NameRef, ValueRef


@pytest.mark.asyncio
async def test_nameref_in_middleware(simple_executor):
    argument = Argument({NAME: NameRef("{origin}_dir"), VALUE: "/tmp"})
    scoped = await argument.run(simple_executor, origin="source")

    assert scoped["source_dir"] == "/tmp"


@pytest.mark.asyncio
async def test_valueref_in_middleware(simple_executor):
    argument = Argument({NAME: NameRef("{origin}_dir"), VALUE: ValueRef("{origin}_dir")})
    scoped = await argument.run(simple_executor, origin="source", source_dir="/tmp")

    assert scoped["source_dir"] == "/tmp"
