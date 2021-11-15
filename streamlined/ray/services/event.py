from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Optional, TypeVar

T = TypeVar("T")
Predicate = Callable[..., bool]

ACTION = Callable[..., None]


def TAUTOLOGY(*args: Any, **kwargs: Any) -> bool:
    return True


def VOID(*args: Any, **kwargs: Any) -> None:
    pass


def before(do: Optional[ACTION] = VOID, when: Optional[Predicate] = TAUTOLOGY):
    """
    Add a hook before decorated function's execution.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            if when(*args, **kwargs):
                do(*args, **kwargs)

            return func(*args, **kwargs)

        return wrapper

    return decorator


def after(
    do: Optional[ACTION] = VOID,
    when: Optional[Predicate] = TAUTOLOGY,
    result_param_name: str = "result",
):
    """
    Add a hook after decorated function's execution.

    Result of decorated function is available through designated `result_param_name`.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            result = func(*args, **kwargs)

            if when(*args, **{result_param_name: result}, **kwargs):
                do(*args, **{result_param_name: result}, **kwargs)

            return result

        return wrapper

    return decorator


if __name__ == "__main__":
    import doctest

    doctest.testmod()
