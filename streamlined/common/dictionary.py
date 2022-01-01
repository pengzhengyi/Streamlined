from collections import UserDict
from typing import Any, Dict, Iterable, Mapping, Optional, TypeVar

from .predicates import IS_DICT, IS_LIST_OF_DICT

K = TypeVar("K")
V = TypeVar("V")


def DEFAULT_KEYERROR(value: Dict[K, V], property: K) -> ValueError:
    return ValueError(f"{value} should have {property} property")


def get_or_raise(value: Dict[K, V], property: K, error: Optional[Exception] = None) -> V:
    try:
        return value[property]
    except KeyError as keyerror:
        if error is None:
            error = DEFAULT_KEYERROR(value, property)
        raise error from keyerror


def get_or_default(mapping: Mapping[K, V], key: K, default: V) -> V:
    try:
        return mapping[key]
    except KeyError:
        return default


def set_if_not_none(dictionary: Dict[Any, Any], key: Any, value: Any) -> bool:
    if value is not None:
        dictionary[key] = value
        return True
    return False


class ProxyDictionary(UserDict):
    """
    A proxy dictionary is intended to provide some more key value
    pairs beyond a mapping object.

    >>> original = {'a': 1, 'b': 2}
    >>> proxied = ProxyDictionary(original, c=3)
    >>> proxied['a'] + proxied['b'] + proxied['c']
    6
    """

    proxy: Mapping[Any, Any]

    def __init__(self, proxy: Mapping[Any, Any], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.proxy = proxy

    def __getitem__(self, key: Any) -> Any:
        try:
            return super().__getitem__(key)
        except KeyError:
            return self.proxy[key]


def findkey(dictionary: Dict[Any, Any], key: Any) -> Iterable[Any]:
    """
    Search for value(s) under given key in a dictionary.

    The search will be recursive.

    >>> list(findkey({'a': 1, 'b': [{'a': 3}, {'b': 4}, {'a': 7}]}, key='a'))
    [1, 3, 7]
    """
    for k, v in dictionary.items():
        if k == key:
            yield v
        else:
            if IS_DICT(v):
                yield from findkey(dictionary=v, key=key)
            elif IS_LIST_OF_DICT(v):
                for new_dict in v:
                    yield from findkey(new_dict, key)


if __name__ == "__main__":
    import doctest

    doctest.testmod()
