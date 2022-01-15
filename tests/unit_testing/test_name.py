import pytest

from streamlined.middlewares import NAME, Name


@pytest.mark.asyncio
async def test_name_set_name_in_scope(simple_executor):
    name = Name({NAME: "foo"})
    scoped = await name.run(simple_executor)
    assert scoped.getmagic(NAME) == "foo"
