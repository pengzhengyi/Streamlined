import pytest

from streamlined.ray.middlewares import NAME, MiddlewareContext, Name


@pytest.mark.asyncio
async def test_name_set_name_in_scope(simple_executor):
    context, _ = MiddlewareContext.new(simple_executor)
    name = Name({NAME: "foo"})
    scoped = await name.apply(context)
    assert scoped.getmagic(NAME) == "foo"