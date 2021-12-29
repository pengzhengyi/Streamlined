from unittest.mock import Mock

import pytest

from streamlined.common import VALUE
from streamlined.middlewares import (
    ARGUMENTS,
    NAME,
    PIPELINE,
    RUNSTAGES,
    Context,
    Pipeline,
)


@pytest.mark.asyncio
async def test_pipeline_simple(simple_executor):
    context, scoping = Context.new(simple_executor)
    mock = Mock()

    def add(a, b):
        mock(a, b)
        return a + b

    pipeline = Pipeline(
        {
            PIPELINE: {
                NAME: "perform add of two numbers",
                ARGUMENTS: [{NAME: "a", VALUE: 10}, {NAME: "b", VALUE: 20}],
                RUNSTAGES: add,
            }
        }
    )

    scoped = await pipeline.apply_into(context)
    mock.assert_called_once_with(10, 20)
