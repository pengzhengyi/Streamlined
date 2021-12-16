import operator
from functools import partial
from typing import Any, Callable, Iterable

IS_NONE = partial(operator.is_, None)


IS_TRUTHY = operator.truth
IS_FALSY = operator.not_


IS_CALLABLE = callable


def IS_NOT_CALLABLE(value) -> bool:
    return not IS_CALLABLE(value)


def IS_DICT(value) -> bool:
    return isinstance(value, dict)


Predicate = Callable[[Any], bool]


def AND(predicates: Iterable[Predicate]) -> Predicate:
    def wrapper(value):
        for predicate in predicates:
            if predicate(value):
                return True
        else:
            return False

    return wrapper
