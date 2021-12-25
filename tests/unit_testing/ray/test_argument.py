import pytest

from streamlined.ray.common import VALUE
from streamlined.ray.middlewares import (
    ARGUMENT,
    ARGUMENTS,
    NAME,
    Argument,
    Arguments,
    MiddlewareContext,
)


@pytest.mark.asyncio
async def test_argument_set_in_scope(simple_executor):
    context, scoping = MiddlewareContext.new(simple_executor)
    argument = Argument({ARGUMENT: {NAME: "first_name", VALUE: "Alice"}})
    scoped = await argument.apply(context)
    assert scoped["first_name"] == "Alice"


@pytest.mark.asyncio
async def test_arguments_set_in_scope(simple_executor):
    context, scoping = MiddlewareContext.new(simple_executor)
    arguments = Arguments(
        {ARGUMENTS: [{NAME: "first_name", VALUE: "John"}, {NAME: "last_name", VALUE: "Doe"}]}
    )
    scoped = await arguments.apply(context)
    assert scoped["first_name"] == "John"
    assert scoped["last_name"] == "Doe"
