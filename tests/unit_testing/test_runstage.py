from typing import Any, Dict, Literal, Union
from unittest.mock import Mock

import pytest

from streamlined.common import VALUE
from streamlined.middlewares import (
    ACTION,
    ARGUMENTS,
    NAME,
    RUNSTAGE,
    RUNSTEPS,
    Runstage,
)
from streamlined.services import Scoped


@pytest.mark.asyncio
async def test_runstage_with_name_example(simple_executor):

    us_convention_mock = Mock()
    chinese_convention_mock = Mock()

    def get_fullname_in_us_convention(first_name, last_name):
        us_convention_mock(first_name, last_name)
        return f"{first_name} {last_name}"

    def get_fullname_in_chinese_convention(first_name, last_name):
        chinese_convention_mock(first_name, last_name)
        return f"{last_name} {first_name}"

    def set_fullname_in_parent_scope(_scoped_: Scoped, full_name: str, convention: str) -> None:
        _scoped_.set(f"full_name_{convention}", full_name, RUNSTAGE)

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

    scoping = await runstage.run(simple_executor)

    us_convention_mock.assert_called_once_with("Alan", "Turing")
    chinese_convention_mock.assert_called_once_with("Alan", "Turing")

    assert scoping.search("full_name_us") == "Alan Turing"
    assert scoping.search("full_name_chinese") == "Turing Alan"


@pytest.mark.asyncio
async def test_runstage_with_dynamic_generated_runsteps(simple_executor):

    us_convention_mock = Mock()
    chinese_convention_mock = Mock()

    def get_fullname_in_us_convention(first_name, last_name):
        us_convention_mock(first_name, last_name)
        return f"{first_name} {last_name}"

    def get_fullname_in_chinese_convention(first_name, last_name):
        chinese_convention_mock(first_name, last_name)
        return f"{last_name} {first_name}"

    def set_fullname_in_parent_scope(_scoped_: Scoped, full_name: str, convention: str) -> None:
        _scoped_.set(f"full_name_{convention}", full_name, RUNSTAGE)

    def create_runstep_config(
        convention: Union[Literal["us"], Literal["chinese"]]
    ) -> Dict[str, Any]:
        get_fullname = (
            get_fullname_in_us_convention
            if convention == "us"
            else get_fullname_in_chinese_convention
        )
        return {
            ARGUMENTS: [
                {NAME: "full_name", VALUE: get_fullname},
                {NAME: "convention", VALUE: convention},
            ],
            ACTION: set_fullname_in_parent_scope,
        }

    def create_runsteps() -> None:
        return [create_runstep_config("chinese"), create_runstep_config("us")]

    runstage = Runstage(
        {
            RUNSTAGE: {
                ARGUMENTS: [
                    {NAME: "first_name", VALUE: "Alan"},
                    {NAME: "last_name", VALUE: "Turing"},
                ],
                RUNSTEPS: create_runsteps,
            }
        }
    )

    scoping = await runstage.run(simple_executor)

    us_convention_mock.assert_called_once_with("Alan", "Turing")
    chinese_convention_mock.assert_called_once_with("Alan", "Turing")

    assert scoping.search("full_name_us") == "Alan Turing"
    assert scoping.search("full_name_chinese") == "Turing Alan"
