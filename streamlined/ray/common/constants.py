from typing import Any


def TAUTOLOGY(*args: Any, **kwargs: Any) -> bool:
    return True


def VOID(*args: Any, **kwargs: Any) -> None:
    pass


async def ASYNC_VOID(*args: Any, **kwargs: Any) -> None:
    pass
