import pytest

from streamlined.ray.common import VALUE
from streamlined.ray.middlewares import ARGUMENT, NAME, Argument, MiddlewareContext


@pytest.mark.asyncio
async def test_argument_set_in_scope(simple_executor):
    context, scoping = MiddlewareContext.new(simple_executor)
    argument = Argument({ARGUMENT: {NAME: "first_name", VALUE: "Alice"}})
    scoped = await argument.apply(context)
    assert scoped["first_name"] == "Alice"
