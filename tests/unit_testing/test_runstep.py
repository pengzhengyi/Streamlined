from unittest.mock import Mock

import pytest

from streamlined.common import VALUE
from streamlined.middlewares import ACTION, NAME, RUNSTEP, Context, Runstep
from streamlined.middlewares.argument import ARGUMENTS


@pytest.mark.asyncio
async def test_runstep_action_requires_arguments(simple_executor):

    context, scoping = Context.new(simple_executor)
    mock = Mock()

    def add(a, b):
        mock(a, b)
        return a + b

    runstep = Runstep(
        {
            RUNSTEP: {
                NAME: "perform add of two numbers",
                ARGUMENTS: [{NAME: "a", VALUE: 10}, {NAME: "b", VALUE: 20}],
                ACTION: add,
            }
        }
    )

    scoped = await runstep.apply_into(context)
    mock.assert_called_once_with(10, 20)
    assert scoped.getmagic(VALUE) == 30
