from __future__ import annotations

import glob
import math
import os
import shelve
from collections import UserDict
from contextlib import suppress
from typing import Any, Iterable, Iterator, MutableMapping, TypeVar, Union

from dill import Pickler, Unpickler, pickles
from pqdict import maxpq
from pympler.asizeof import flatsize

from .storage_option import HybridStorageOption, PersistentStorageOption, StorageOption

shelve.Pickler = Pickler
shelve.Unpickler = Unpickler

T = TypeVar("T")


class StorageProvider(MutableMapping[str, Any]):
    """
    StorageProvider is an abstract class requiring a MutableMapping provider.

    In addition to normal MutableMapping operations, derived classes are
    recommended to implement the following operations:

    + `close` operation which does proper clean up
    + `free` which offsets the memory footprint by operations like
      clearing the data, removing the persistent file, or removing a
      database.
    """

    __slots__ = ("cleanup_at_close",)

    @classmethod
    def of(cls, storage_option: StorageOption) -> StorageProvider:
        """
        Create a storage provider from a storage option.
        """
        return cls(*storage_option.args, **storage_option.kwargs)

    def __init__(self, cleanup_at_close: bool = False) -> None:
        super().__init__()
        self.cleanup_at_close = cleanup_at_close

    def __enter__(self: T) -> T:
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.close()

    def __getitem__(self, __k: str) -> Any:
        raise NotImplementedError()

    def __setitem__(self, __k: str, __v: Any) -> None:
        raise NotImplementedError()

    def __len__(self) -> int:
        raise NotImplementedError()

    def __delitem__(self, __k: str) -> None:
        raise NotImplementedError()

    def __iter__(self) -> Iterator[Any]:
        raise NotImplementedError()

    def cleanup(self) -> None:
        """
        Offset the memory usage.
        """
        return

    def close(self) -> None:
        """
        Proper clean up. For example, make sure data is synced to storage/database.

        Once this function is called, no more writes should be issued to this storage
        provider.
        """
        if self.cleanup_at_close:
            self.cleanup()


class InMemoryStorageProvider(UserDict[str, Any], StorageProvider):
    """
    Use a dictionary as a storage provider.
    """

    def __init__(self, cleanup_at_close: bool = False) -> None:
        super().__init__()
        self.cleanup_at_close = cleanup_at_close

    def cleanup(self) -> None:
        self.clear()
        super().cleanup()


class PersistentStorageProvider(StorageProvider):
    """
    Provides a persistent dictionary.

    Reference
    ------
    [shelve]https://docs.python.org/3/library/shelve.html)
    """

    __slots__ = ("shelf", "filename")

    @classmethod
    def of(
        cls, filename: str, storage_option: PersistentStorageOption
    ) -> PersistentStorageProvider:
        return cls(filename, *storage_option.args, **storage_option.kwargs)

    def __init__(self, filename: str, cleanup_at_close: bool = False) -> None:
        self._init_shelf(filename)
        super().__init__(cleanup_at_close)

    def _init_shelf(self, filename: str) -> None:
        self.filename = filename
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        self.shelf = shelve.open(filename)

    def __getitem__(self, __k: str) -> Any:
        return self.shelf.__getitem__(__k)

    def __setitem__(self, __k: str, __v: Any) -> None:
        """
        Set a mapping from key to value.

        Raises
        ------
        AttributeError
            When a value cannot be pickled
        """
        self.shelf.__setitem__(__k, __v)
        self.shelf.sync()

    def __len__(self) -> int:
        return self.shelf.__len__()

    def __delitem__(self, __k: str) -> None:
        return self.shelf.__delitem__(__k)

    def __iter__(self) -> Iterator[Any]:
        return self.shelf.__iter__()

    def _get_shelf_files(self) -> Iterable[str]:
        yield from glob.iglob(f"{self.filename}.*")

    def cleanup(self) -> None:
        for savefile in self._get_shelf_files():
            os.remove(savefile)

        super().cleanup()

    def close(self) -> None:
        self.shelf.close()
        super().close()


class HybridStorageProvider(StorageProvider):
    """
    HybridStorageProvider combines a storing-in-memory approach and a
    storing-in-storage option.

    Memory Limit
    ------
    At creation, HybridStorageProvider can specify a `memory_limit`. Until
    the purgeable memory exceeds this limit -- the items that can be
    serialized to store in storage, all mappings will be stored in
    InMemoryStorageProvider. Then whenever the memory footprint is about
    to exceed, HybridStorageProvider will transfer the most expensive mappings to PersistentProvider until the live memory usage is below the
    limit again.

    However, oppositely, deleting a serializable item will update the used
    memory estimation but will not cause mappings to transfer from
    PersistentProvider to InMemoryStorageProvider.

    Note that the memory usage is roughly estimated. For example, if a
    mutable entry like a list is stored and one element is appended to the
    list. The estimation will not update correctly. However, such operation
    is not recommended at first place. See
    [shelve](https://docs.python.org/3/library/shelve.html)
    for more detailed explanation. To achieve the same effect, please do:

    ```
    temp = d['xx']             # extracts the copy
    temp.append(5)             # mutates the copy
    d['xx'] = temp             # stores the copy right back, to persist it
    ```
    """

    __slots__ = (
        "_memory_limit",
        "_purgeables",
        "_memory",
        "_storage",
    )

    @classmethod
    def of(cls, filename: str, storage_option: HybridStorageOption) -> HybridStorageProvider:
        return cls(filename, *storage_option.args, **storage_option.kwargs)

    @property
    def purgeable_memory(self) -> int:
        """
        The amount of purgeable memory -- memory that can be cached
        to storage.
        """
        if self.use_memory:
            return sum(self._purgeables.values())
        else:
            return 0

    @property
    def use_memory(self) -> bool:
        """
        Whether any mapping might be stored in memory.
        """
        return self._memory_limit > 0

    @property
    def use_memory_only_as_storage_fallback(self) -> bool:
        """
        This condition is True if and only if both memory storage are used
        but memory will only store unpickleable mappings.
        """
        return 0 < self._memory_limit < 1

    @property
    def use_storage(self) -> bool:
        """
        Whether any mapping might be stored in disk.
        """
        return self._memory_limit != math.inf

    def __init__(
        self,
        filename: str,
        memory_limit: Union[float, int],
        cleanup_at_close: bool = False,
    ) -> None:
        super().__init__(cleanup_at_close)
        self._memory_limit = memory_limit
        self._init_memory_provider()
        self._init_persistent_memory_storage_provider(filename, cleanup_at_close)

    def _init_memory_provider(self) -> None:
        if self.use_memory:
            self._purgeables = maxpq()
            self._memory = InMemoryStorageProvider()

    def _init_persistent_memory_storage_provider(
        self, filename: str, cleanup_at_close: bool
    ) -> None:
        if self.use_storage:
            self._storage = PersistentStorageProvider(filename, cleanup_at_close)

    def __getitem__(self, __k: str) -> Any:
        if self.use_memory:
            with suppress(KeyError):
                return self._memory.__getitem__(__k)
        if self.use_storage:
            return self._storage.__getitem__(__k)

        raise KeyError(f"Cannot find key {__k}")

    def __contains__(self, __o: object) -> bool:
        if self.use_memory and self._memory.__contains__(__o):
            return True
        if self.use_storage and self._storage.__contains__(__o):
            return True
        return False

    def __len__(self) -> int:
        length = 0

        if self.use_memory:
            length += self._memory.__len__()
        if self.use_storage:
            length += self._storage.__len__()

        return length

    def __iter__(self) -> Iterator[Any]:
        if self.use_memory:
            yield from self._memory.__iter__()
        if self.use_storage:
            yield from self._storage.__iter__()

    def __delitem__(self, __k: str) -> None:
        if self.use_memory:
            with suppress(KeyError):
                self._memory.__delitem__(__k)
                self._purgeables.__delitem__(__k)
        if self.use_storage:
            self._storage.__delitem__(__k)

    def __setitem__(self, __k: str, __v: Any) -> None:
        if self.use_memory_only_as_storage_fallback:
            (self._storage if pickles(__v) else self._memory).__setitem__(__k, __v)
            return

        if self.use_memory:
            self._memory.__setitem__(__k, __v)

            if pickles(__v):
                # pickleable -> consider whether to store in storage
                new_cost: int = flatsize(__v)
                self._purgeables[__k] = new_cost

                if self.use_storage:
                    self._rebalance_memory()

        elif self.use_storage:
            self._storage.__setitem__(__k, __v)

    def _rebalance_memory(self) -> None:
        limit = self._memory_limit
        usage = self.purgeable_memory

        # since `self._purgeables` stores only pickleable
        # objects, usage can be decreased to 0 and will at some moment
        # smaller than limit

        while usage > limit:
            # from memory to storage
            key, cost = self._purgeables.popitem()
            value = self._memory.pop(key)
            self._storage.__setitem__(key, value)
            usage -= cost

    def cleanup(self) -> None:
        if self.use_memory:
            self._memory.cleanup()
        if self.use_storage:
            self._storage.cleanup()

        super().cleanup()

    def close(self) -> None:
        if self.use_memory:
            self._memory.close()
        if self.use_storage:
            self._storage.close()

        super().close()
