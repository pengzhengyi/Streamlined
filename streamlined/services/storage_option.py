from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from functools import partial
from typing import Any, Callable, Mapping, Sequence, Tuple, TypeVar

T = TypeVar("T")

TArguments = Tuple[Sequence[Any], Mapping[str, Any]]


@dataclass
class Arguments:
    """
    Method arguments.
    """

    args: Sequence[Any]
    kwargs: Mapping[str, Any]

    def __call__(self, method: Callable[..., T]) -> T:
        return method(*self.args, **self.kwargs)

    def partial(self, method: Callable[..., T]) -> Callable[..., T]:
        """
        Partially bind a method.
        """
        return partial(method, *self.args, **self.kwargs)


class StorageOption(Arguments, Enum):
    """
    A base class for StorageOption.

    Each storage option should be an instance of Arguments encapsulating constructor
    arguments.
    """


class InMemoryStorageOption(StorageOption):
    """
    StorageOption
    """

    PERSISTENT: TArguments = (tuple(), dict(cleanup_at_close=False))
    "storage will not be released at `close`"

    TRANSIENT: TArguments = (tuple(), dict(cleanup_at_close=False))
    "storage will be released at `close`"


PersistentStorageOption = InMemoryStorageOption


DEFAULT_BUFFER_SIZE = 1024 * 1024


class HybridStorageOption(StorageOption):
    """
    Describes flavors for `HybridStorageProvider` storage option.
    """

    PERSISTENT_MEMORY: TArguments = (
        tuple(),
        dict(memory_limit=math.inf, cleanup_at_close=False),
    )
    "Everything will be stored in memory and memory will not be released at `close`"

    TRANSIENT_MEMORY: TArguments = (
        tuple(),
        dict(memory_limit=math.inf, cleanup_at_close=True),
    )
    "Everything will be stored in memory and memory will  be released at `close`"

    PERSISTENT_STORAGE: TArguments = (
        tuple(),
        dict(memory_limit=0, cleanup_at_close=False),
    )
    "Everything will be stored in storage and storage will not be released at `close`"

    TRANSIENT_STORAGE: TArguments = (
        tuple(),
        dict(memory_limit=0, cleanup_at_close=True),
    )
    "Everything will be stored in storage and storage will be released at `close`"

    PERSISTENT_HYBRID: TArguments = (
        tuple(),
        dict(memory_limit=DEFAULT_BUFFER_SIZE, cleanup_at_close=False),
    )
    "Up to DEFAULT_BUFFER_SIZE will be stored in memory and everything else will be stored in storage. Both memory and storage will not be released at `close`"

    TRANSIENT_HYBRID: TArguments = (
        tuple(),
        dict(memory_limit=DEFAULT_BUFFER_SIZE, cleanup_at_close=True),
    )
    "Up to DEFAULT_BUFFER_SIZE will be stored in memory and everything else will be stored in storage. Both memory and storage will be released at `close`"
