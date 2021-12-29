import pytest

from streamlined.ray.common import run


@pytest.mark.asyncio
async def test_run_with_argstr():
    argstr = "echo Hello World"
    result = await run(argstr)
    assert result.stdout.strip() == b"Hello World"


@pytest.mark.asyncio
async def test_run_with_list_of_str():
    argstr = ["date"]
    result = await run(argstr)
    assert result.returncode == 0
