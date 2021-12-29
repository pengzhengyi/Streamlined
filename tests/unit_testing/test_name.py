import pytest

from streamlined.middlewares import NAME, Context, Name


@pytest.mark.asyncio
async def test_name_set_name_in_scope(simple_executor):
    context, _ = Context.new(simple_executor)
    name = Name({NAME: "foo"})
    scoped = await name.apply_into(context)
    assert scoped.getmagic(NAME) == "foo"
