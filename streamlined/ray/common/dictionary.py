from typing import Dict, Optional, TypeVar

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
