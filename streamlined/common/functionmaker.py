import inspect
import re
from asyncio import iscoroutinefunction
from functools import partial
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


def create(obj, body, evaldict, defaults=None, doc=None, module=None, addsource=True, **attrs):
    """
    Create a function from the strings name, signature and body.
    evaldict is the evaluation dictionary. If addsource is true an
    attribute __source__ is added to the result. The attributes attrs
    are added, if any.

    Note
    ------

    Same as the `FunctionMaker.create` except that classmethod fail to
    account for edge case where an async function body contains `return`.

    For example:

    ```
    async def IDENTITY(return_value):
        return return_value


    FunctionMaker.create('WILL_RAISE_SYNTAX_ERROR()', 'return IDENTITY(return_value=actual_return_value)', dict(IDENTITY=IDENTITY, _call_=IDENTITY, actual_return_value=10), addsource=True)
    ```

    Will raise the following error:

    ```
    Traceback (most recent call last):
        File "<stdin>", line 1, in <module>
        File "/opt/conda/lib/python3.9/site-packages/decorator.py", line 196, in create
            return self.make(body, evaldict, addsource, **attrs)
        File "/opt/conda/lib/python3.9/site-packages/decorator.py", line 159, in make
            code = compile(src, filename, 'single')
        File "<decorator-gen-4>", line 2
            return await IDENTITY(return await_value=actual_return await_value)
                                ^
        SyntaxError: invalid syntax

    To fix, we need to match on 'return ' rather than 'return'
    ```
    """
    if isinstance(obj, str):  # "name(signature)"
        name, rest = obj.strip().split("(", 1)
        signature = rest[:-1]  # strip a right parens
        func = None
    else:  # a function
        name = None
        signature = None
        func = obj
    self = FunctionMaker(func, name, signature, defaults, doc, module)
    ibody = "\n".join("    " + line for line in body.splitlines())
    caller = evaldict.get("_call_")  # when called from `decorate`
    if caller and iscoroutinefunction(caller):
        rawbody = "async def %(name)s(%(signature)s):\n" + ibody
        body = re.sub(r"(^|\s)return(\s)", r"\1return await\2", rawbody)
    else:
        body = "def %(name)s(%(signature)s):\n" + ibody
    return self.make(body, evaldict, addsource, **attrs)


def bound(function: Callable[..., T], *args: Any, **kwargs: Any) -> Callable[[], T]:
    """
    Similar to [`functools.partial`](https://docs.python.org/3/library/functools.html#functools.partial), except a new function is created with `exec`.

    This can be a substitute for `functools.partial` when binding all arguments
    and works better with callable class and `asyncio.iscoroutinefunction` as it
    will remake a wrapper function.
    """
    if inspect.isfunction(function):
        function_newname = f"bound_{function.__name__}"
    elif isinstance(function, partial):
        # rebound a partially bound function such that it is fully bound
        function = function.func
        function_newname = f"rebound_{function.__name__}"
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
    return create(
        f"{function_newname}()",
        f"return function({parameters})",
        dict(function=function, _call_=function, **arg_values, **kwarg_values),
        addsource=True,
    )


if __name__ == "__main__":
    import doctest

    doctest.testmod()
