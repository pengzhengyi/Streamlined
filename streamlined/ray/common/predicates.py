import operator
from functools import partial
from typing import Any, Callable, List

IS_NONE = partial(operator.is_, None)


IS_TRUTHY = operator.truth
IS_FALSY = operator.not_


IS_CALLABLE = callable


def IS_NOT_CALLABLE(value) -> bool:
    return not IS_CALLABLE(value)


def IS_DICT(value) -> bool:
    return isinstance(value, dict)


def IS_NOT_DICT(value) -> bool:
    return not IS_DICT(value)


def IS_STR(value) -> bool:
    return isinstance(value, str)


def IS_NOT_STR(value) -> bool:
    return not IS_STR(value)


def IS_LIST(value) -> bool:
    return isinstance(value, list)


def IS_NOT_LIST(value) -> bool:
    return not IS_LIST(value)


def IS_NOT_LIST_OF_DICT(value: Any) -> bool:
    if IS_LIST(value):
        for listitem in value:
            if IS_NOT_DICT(listitem):
                return True
        return False
    else:
        return True


Predicate = Callable[[Any], bool]


def AND(*predicates: List[Predicate]) -> Predicate:
    def wrapper(value):
        for predicate in predicates:
            if not predicate(value):
                return False

        return True

    return wrapper
