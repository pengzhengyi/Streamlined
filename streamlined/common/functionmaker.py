import inspect
from itertools import chain
from typing import Any, Callable, TypeVar

from decorator import FunctionMaker

T = TypeVar("T")


def create_identity_function(parameter_name: str) -> Callable[[T], T]:
    """
    Create a function that takes a parameter with given name and
    return that argument.

    New function will be named: `get_<parameter_name>`

    >>> get_foo = create_identity_function('foo')
    >>> get_foo('bar')
    'bar'
    """
    return FunctionMaker.create(
        f"get_{parameter_name}({parameter_name})",
        f"return {parameter_name}",
        dict(),
        addsource=True,
    )


def rewrite_function_parameters(
    function: Callable[..., T], function_newname: str, *args: str, **kwargs: str
) -> Callable[..., T]:
    """
    Provide functionality to rewrite a function's parameter list.

    >>> exponent = rewrite_function_parameters(pow, 'exponent', 'x', 'y')
    >>> exponent(2, 4) == pow(2, 4)
    True
    """
    parameters = ", ".join(chain(args, kwargs.values()))
    arguments = ", ".join(
        chain(args, (f"{arg_name}={param_name}" for arg_name, param_name in kwargs.items()))
    )
    return FunctionMaker.create(
        f"{function_newname}({parameters})",
        f"return function({arguments})",
        dict(function=function, _call_=function),
        addsource=True,
    )


def bound(function: Callable[..., T], *args: Any, **kwargs: Any) -> Callable[[], T]:
    """
    Similar to [`functools.partial`](https://docs.python.org/3/library/functools.html#functools.partial), except a new function is created with `exec`.

    This can be a substitute for `functools.partial` when binding all arguments
    and works better with callable class and `asyncio.iscoroutinefunction` as it
    will remake a wrapper function.
    """
    if inspect.isfunction(function):
        function_newname = f"bound_{function.__name__}"
    else:
        function_newname = f"call_{function.__class__.__name__}"
        function = function.__call__

    parameters = ", ".join(
        chain(
            (f"_bound_arg_{i}_value_" for i in range(len(args))),
            (f"{param_name}=_bound_kwarg_{param_name}_value_" for param_name in kwargs),
        )
    )
    arg_values = {f"_bound_arg_{i}_value_": arg for i, arg in enumerate(args)}
    kwarg_values = {
        f"_bound_kwarg_{param_name}_value_": param_value
        for param_name, param_value in kwargs.items()
    }
    return FunctionMaker.create(
        f"{function_newname}()",
        f"return function({parameters})",
        dict(function=function, _call_=function, **arg_values, **kwarg_values),
        addsource=True,
    )


if __name__ == "__main__":
    import doctest

    doctest.testmod()
