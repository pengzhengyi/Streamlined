from unittest.mock import Mock

import pytest

from streamlined.ray.common import VALUE
from streamlined.ray.middlewares import (
    ACTION,
    NAME,
    RUNSTEP,
    RUNSTEPS,
    Context,
    Runstage,
    Runstep,
)
from streamlined.ray.middlewares.argument import ARGUMENTS
from streamlined.ray.middlewares.runstage import RUNSTAGE
from streamlined.ray.services.scoping import Scoped


@pytest.mark.asyncio
async def test_runstage_with_name_example(simple_executor):
    context, scoping = Context.new(simple_executor)
    us_convention_mock = Mock()
    chinese_convention_mock = Mock()

    def get_fullname_in_us_convention(first_name, last_name):
        us_convention_mock(first_name, last_name)
        return f"{first_name} {last_name}"

    def get_fullname_in_chinese_convention(first_name, last_name):
        chinese_convention_mock(first_name, last_name)
        return f"{last_name} {first_name}"

    def set_fullname_in_parent_scope(_scoped_: Scoped, full_name: str, convention: str) -> None:
        _scoped_.set(f"full_name_{convention}", full_name, 2)

    runstage = Runstage(
        {
            RUNSTAGE: {
                ARGUMENTS: [
                    {NAME: "first_name", VALUE: "Alan"},
                    {NAME: "last_name", VALUE: "Turing"},
                ],
                RUNSTEPS: [
                    {
                        ARGUMENTS: [
                            {NAME: "full_name", VALUE: get_fullname_in_us_convention},
                            {NAME: "convention", VALUE: "us"},
                        ],
                        ACTION: set_fullname_in_parent_scope,
                    },
                    {
                        ARGUMENTS: [
                            {NAME: "full_name", VALUE: get_fullname_in_chinese_convention},
                            {NAME: "convention", VALUE: "chinese"},
                        ],
                        ACTION: set_fullname_in_parent_scope,
                    },
                ],
            }
        }
    )

    scoped = await runstage.apply_into(context)

    us_convention_mock.assert_called_once_with("Alan", "Turing")
    chinese_convention_mock.assert_called_once_with("Alan", "Turing")

    assert scoped.get("full_name_us") == "Alan Turing"
    assert scoped.get("full_name_chinese") == "Turing Alan"
