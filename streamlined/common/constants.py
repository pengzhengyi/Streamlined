from __future__ import annotations

from typing import Any


def TAUTOLOGY(*args: Any, **kwargs: Any) -> True:
    return True


def CONTRADICTION(*args: Any, **kwargs: Any) -> False:
    return False


def VOID(*args: Any, **kwargs: Any) -> None:
    pass


async def ASYNC_VOID(*args: Any, **kwargs: Any) -> None:
    pass


def TAUTOLOGY_FACTORY() -> TAUTOLOGY:
    return TAUTOLOGY


def NOOP():
    return None


def RETURN_TRUE():
    return True


def RETURN_FALSE():
    return False
