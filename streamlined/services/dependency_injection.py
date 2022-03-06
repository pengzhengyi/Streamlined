from __future__ import annotations

import inspect
from inspect import Parameter
from typing import Any, Callable, Dict, List, Mapping

from ..common import IS_EMPTY_BOUND_ARGUMENTS, bound, get_or_default


class DependencyInjection:
    """
    DependencyInjection will inspect a callable's signature.
    Then for each parameter, it will try to resolve from specified providers and
    return a function that is the fully bound version of callable.

    Act as injector in [DependencyInjection](https://en.wikipedia.org/wiki/Dependency_injection).

    >>> def add(a, b = 0, *nums, d, e = 0, **kwnums):
    ...     return a + b + sum(nums) + d + e + sum(kwnums.values())
    >>> ba = DependencyInjection.inject_callable(add, {'a': 1, 'nums': [10, 100], 'd': 1000, 'kwnums': {'f': 10000}})
    >>> add(*ba.args, **ba.kwargs)
    11111
    """

    @classmethod
    def inject_signature(
        cls, signature: inspect.Signature, providers: Mapping[Any, Any]
    ) -> inspect.BoundArguments:
        args: List[Any] = []
        kwargs: Dict[Any, Any] = dict()

        for name, parameter in signature.parameters.items():
            if (
                parameter.kind == Parameter.POSITIONAL_ONLY
                or parameter.kind == Parameter.POSITIONAL_OR_KEYWORD
            ):
                if parameter.default == Parameter.empty:
                    args.append(providers[name])
                else:
                    args.append(get_or_default(providers, name, parameter.default))
            elif parameter.kind == Parameter.VAR_POSITIONAL:
                args.extend(get_or_default(providers, name, default=[]))
            elif parameter.kind == Parameter.KEYWORD_ONLY:
                if parameter.default == Parameter.empty:
                    kwargs[name] = providers[name]
                else:
                    kwargs[name] = get_or_default(providers, name, parameter.default)
            elif parameter.kind == Parameter.VAR_KEYWORD:
                kwargs.update(get_or_default(providers, name, default=dict()))

        return signature.bind(*args, **kwargs)

    @classmethod
    def inject_callable(
        cls, _callable: Callable[..., Any], providers: Mapping[Any, Any]
    ) -> inspect.BoundArguments:
        signature = inspect.signature(_callable)
        try:
            return cls.inject_signature(signature, providers)
        except KeyError as keyerror:
            # assist debugging
            raise KeyError(f"cannot resolve arguments for {_callable}") from keyerror

    @classmethod
    def bind_callable(
        cls, _callable: Callable[..., Any], bound_arguments: inspect.BoundArguments
    ) -> Callable[[], Any]:
        if IS_EMPTY_BOUND_ARGUMENTS(bound_arguments):
            return _callable

        return bound(_callable, *bound_arguments.args, **bound_arguments.kwargs)

    @classmethod
    def prepare(
        cls, _callable: Callable[..., Any], providers: Mapping[Any, Any]
    ) -> Callable[[], Any]:
        bound_arguments = cls.inject_callable(_callable, providers)
        return cls.bind_callable(_callable, bound_arguments)


if __name__ == "__main__":
    import doctest

    doctest.testmod()
