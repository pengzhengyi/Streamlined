from collections import UserDict
from typing import Any, Dict, Mapping, Optional, TypeVar

K = TypeVar("K")
V = TypeVar("V")


def DEFAULT_KEYERROR(value: Dict[K, V], property: K):
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


if __name__ == "__main__":
    import doctest

    doctest.testmod()
