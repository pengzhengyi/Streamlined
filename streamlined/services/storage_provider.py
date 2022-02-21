from __future__ import annotations

import glob
import math
import os
import pickle
import shelve
from collections import UserDict
from contextlib import suppress
from pickle import PickleError
from typing import Any, Iterable, Iterator, List, MutableMapping, Optional, Tuple, Union
from warnings import warn

from pqdict import maxpq
from pympler.asizeof import flatsize

from .storage_option import HybridStorageOption, PersistentStorageOption, StorageOption


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

    def __enter__(self) -> StorageProvider:
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

    def memory_footprint(self, key: Optional[str] = None) -> int:
        """
        Get the memory footprint of current provider.

        When key is specified, get the memory memory_footprint of specified value.
        """
        if key is None:
            return flatsize(self)
        else:
            value = self.__getitem__(key)
            return flatsize(value)

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

    def memory_footprint(self, key: Optional[str] = None) -> int:
        if key is None:
            return sum(os.path.getsize(savefile) for savefile in self._get_shelf_files())

        return super().memory_footprint(key)

    def cleanup(self) -> None:
        for savefile in self._get_shelf_files():
            os.remove(savefile)

        super().cleanup()

    def close(self) -> None:
        self.shelf.close()
        super().close()


class HybridStorageProvider(StorageProvider):
    """
    HybridStorageProvider combines an in-memory storage approach and a
    persistent storage option.

    Memory Limit
    ------
    At creation, HybridStorageProvider can specify a `memory_limit`. Until
    the memory footprint exceeds this limit, all mappings will be stored in
    InMemoryStorageProvider. Then whenever the memory footprint is about
    to exceed, HybridStorageProvider will transfer the most expensive mappings to PersistentProvider until the live memory usage is below the
    limit again.

    Reversely, deleting an item will update the memory footprint
    estimation but not cause tranferring of mappings from
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
        "_in_memory_priority_queue",
        "_in_memory_storage",
        "_persistent_storage",
    )

    @classmethod
    def of(cls, filename: str, storage_option: HybridStorageOption) -> HybridStorageProvider:
        return cls(filename, *storage_option.args, **storage_option.kwargs)

    @property
    def _in_memory_footprint(self) -> int:
        if self.has_in_memory_storage:
            return sum(self._in_memory_priority_queue.values())
        else:
            return 0

    @property
    def has_in_memory_storage(self) -> bool:
        """
        Whether any mapping might be stored in memory.
        """
        return self._memory_limit > 0

    @property
    def has_persistent_storage(self) -> bool:
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
        self._init_in_memory_storage_provider()
        self._init_persistent_memory_storage_provider(filename, cleanup_at_close)

    def _init_in_memory_storage_provider(self) -> None:
        if self.has_in_memory_storage:
            self._in_memory_priority_queue = maxpq()
            self._in_memory_storage = InMemoryStorageProvider()

    def _init_persistent_memory_storage_provider(
        self, filename: str, cleanup_at_close: bool
    ) -> None:
        if self.has_persistent_storage:
            self._persistent_storage = PersistentStorageProvider(filename, cleanup_at_close)

    def __getitem__(self, __k: str) -> Any:
        if self.has_in_memory_storage:
            with suppress(KeyError):
                return self._in_memory_storage.__getitem__(__k)
        if self.has_persistent_storage:
            return self._persistent_storage.__getitem__(__k)

        raise KeyError(f"Cannot find key {__k}")

    def __len__(self) -> int:
        length = 0

        if self.has_in_memory_storage:
            length += self._in_memory_storage.__len__()
        if self.has_persistent_storage:
            length += self._persistent_storage.__len__()

        return length

    def __iter__(self) -> Iterator[Any]:
        if self.has_in_memory_storage:
            yield from self._in_memory_storage.__iter__()
        if self.has_persistent_storage:
            yield from self._persistent_storage.__iter__()

    def __delitem__(self, __k: str) -> None:
        if self.has_in_memory_storage:
            with suppress(KeyError):
                self._in_memory_storage.__delitem__(__k)
                self._in_memory_priority_queue.__delitem__(__k)
        if self.has_persistent_storage:
            self._persistent_storage.__delitem__(__k)

    def __setitem__(self, __k: str, __v: Any) -> None:
        if self.has_in_memory_storage:
            # save in memory
            new_cost: int = flatsize(__v)
            try:
                # stored in memory
                existing_cost: int = self._in_memory_priority_queue[__k]
                if new_cost != existing_cost:
                    self._in_memory_priority_queue[__k] = new_cost
            except KeyError:
                self._in_memory_priority_queue[__k] = new_cost
            self._in_memory_storage.__setitem__(__k, __v)

            if self.has_persistent_storage:
                self._rebalance_memory()
        elif self.has_persistent_storage:
            self._persistent_storage.__setitem__(__k, __v)

    def _rebalance_memory(self) -> None:
        unpickleables: List[Tuple[str, Any, int]] = []

        limit = self._memory_limit
        usage = self._in_memory_footprint
        while self._in_memory_priority_queue and usage > limit:
            key, cost = self._in_memory_priority_queue.popitem()
            value = self._in_memory_storage.pop(key)
            try:
                pickle.dumps(value)
                self._persistent_storage.__setitem__(key, value)
                usage -= cost
            except (PickleError, AttributeError):
                unpickleables.append((key, value, cost))

        for key, value, cost in unpickleables:
            self._in_memory_priority_queue.additem(key, cost)
            self._in_memory_storage[key] = value

        if usage > limit:
            warn(
                f"Memory usage {usage} exceeds limit {limit} since remaining are all not pickleable",
                category=RuntimeWarning,
            )

    def memory_footprint(self, key: Optional[str] = None) -> int:
        if key is None:
            footprint = 0
            if self.has_in_memory_storage:
                footprint += self._in_memory_storage.memory_footprint()
            if self.has_persistent_storage:
                footprint += self._persistent_storage.memory_footprint()
            return footprint
        else:
            return super().memory_footprint(key)

    def cleanup(self) -> None:
        if self.has_in_memory_storage:
            self._in_memory_storage.cleanup()
        if self.has_persistent_storage:
            self._persistent_storage.cleanup()

        super().cleanup()

    def close(self) -> None:
        if self.has_in_memory_storage:
            self._in_memory_storage.close()
        if self.has_persistent_storage:
            self._persistent_storage.close()

        super().close()
