from __future__ import annotations

import inspect
from inspect import Parameter
from typing import Any, Callable, ClassVar, Iterable, List, Mapping, Optional

from .service import Service


class DependencyInjection(Service):
    """
    Act as injector in [DependencyInjection](https://en.wikipedia.org/wiki/Dependency_injection).

    >>> list(DependencyInjection.inject(['x'], {'x': 1}))
    [1]
    >>> def add(a, b = 0, *nums, d, e = 0, **kwnums):
    ...     return a + b + sum(nums) + d + e + sum(kwnums.values())
    >>> ba = DependencyInjection.inject_callable(add, {'a': 1, 'nums': [10, 100], 'd': 1000, 'kwnums': {'f': 10000}})
    >>> add(*ba.args, **ba.kwargs)
    11111
    """

    MISSING: ClassVar[Ellipsis] = ...

    @classmethod
    def inject(
        cls,
        requirements: Iterable[Any],
        providers: Mapping[Any, Any],
        defaults: Optional[Iterable[Any]] = None,
    ) -> Iterable[Any]:
        """
        Search in providers for each requirement.
        """
        if defaults:
            for requirement, default in zip(requirements, defaults):
                yield providers[requirement] if default is cls.MISSING else providers.get(
                    requirement, default
                )
        else:
            for requirement in requirements:
                yield providers[requirement]

    @classmethod
    def inject_callable(
        cls, _callable: Callable[..., Any], providers: Mapping[Any, Any]
    ) -> inspect.BoundArguments:
        signature = inspect.signature(_callable)

        args: List[Any] = []
        kwargs: Mapping[Any, Any] = dict()

        for name, parameter in signature.parameters.items():
            if (
                parameter.kind == Parameter.POSITIONAL_ONLY
                or parameter.kind == Parameter.POSITIONAL_OR_KEYWORD
            ):
                if parameter.default == Parameter.empty:
                    args.append(providers[name])
                else:
                    args.append(providers.get(name, parameter.default))
            elif parameter.kind == Parameter.VAR_POSITIONAL:
                args.extend(providers.get(name, []))
            elif parameter.kind == Parameter.KEYWORD_ONLY:
                if parameter.default == Parameter.empty:
                    kwargs[name] = providers[name]
                else:
                    kwargs[name] = providers.get(name, parameter.default)
            elif parameter.kind == Parameter.VAR_KEYWORD:
                kwargs.update(providers.get(name, dict()))

        return signature.bind(*args, **kwargs)


if __name__ == "__main__":
    import doctest

    doctest.testmod()