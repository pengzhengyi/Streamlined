from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Optional, Type, TypeVar, Union

from .service import Service

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


def raises(
    do: Optional[ACTION] = VOID,
    when: Optional[Predicate] = TAUTOLOGY,
    expected_exception: Type[BaseException] = Exception,
    exception_param_name: str = "_exception_",
):
    """
    Add a hook to catch expected exception.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return func(*args, **kwargs)
            except expected_exception as exception:
                if when(*args, **{exception_param_name: exception}, **kwargs):
                    if isinstance(
                        result := do(*args, **{exception_param_name: exception}, **kwargs),
                        BaseException,
                    ):
                        raise result from exception
                    else:
                        return result

        return wrapper

    return decorator


def after(
    do: Optional[ACTION] = VOID,
    when: Optional[Predicate] = TAUTOLOGY,
    result_param_name: str = "_result_",
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


React = Union[before, after, raises]


class Reaction(Service):
    """
    Reaction is an abstract class that should be subclassed to use.

    `react` or `when` should be overridden with desired behavior.

    `bind` can be called to produce a decorator that binds this handler to a function.
    """

    def when(self, *args: Any, **kwargs: Any) -> bool:
        """
        Determines whether `react` method should be called.
        """
        return True

    def react(self, *args: Any, **kwargs: Any) -> None:
        """
        Perform an action at specific timings of registered function.
        """
        pass

    def bind(self, at: Union[before, after, raises]):
        return at(do=self.react, when=self.when)


if __name__ == "__main__":
    import doctest

    doctest.testmod()
