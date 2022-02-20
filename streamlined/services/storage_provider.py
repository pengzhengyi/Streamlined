from __future__ import annotations

import glob
import os
import shelve
from collections import UserDict
from typing import Any, Iterable, Iterator, MutableMapping, Optional

from pqdict import maxpq
from pympler import asizeof


class StorageProvider(MutableMapping[str, Any]):
    """
    StorageProvider is an abstract class requiring a MutableMapping provider.

    In addition to normal MutableMapping operations, derived classes are
    recommended to implement a `close` operation which offset the memory
    footprint. Such operation might involves clearing the data, removing the
    persistent file, or removing a database.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__()

        for key, value in kwargs.items():
            self.__setitem__(key, value)

    def __enter__(self) -> StorageProvider:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
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

    def free(self) -> None:
        return self.close()

    def close(self) -> None:
        """
        Offset the memory usage of this provider. The default implementation
        does nothing.
        """
        return

    def memory_footprint(self, key: Optional[str] = None) -> int:
        """
        Get the memory footprint of current provider.

        When key is specified, get the memory memory_footprint of specified value.
        """
        if key is None:
            return asizeof.asizeof(self)
        else:
            value = self.__getitem__(key)
            return asizeof.asizeof(value)


class InMemoryStorageProvider(UserDict[str, Any], StorageProvider):
    """
    Use a dictionary as a storage provider.
    """

    def free(self) -> None:
        self.clear()


class PersistentStorageProvider(StorageProvider):
    """
    Provides a persistent dictionary.

    Reference
    ------
    [shelve]https://docs.python.org/3/library/shelve.html)
    """

    __slots__ = ("shelf", "_filename", "remove_at_close")

    def __init__(self, __filename: str, __remove_at_close: bool = False, **kwargs: Any) -> None:
        self._init_shelf(__filename, __remove_at_close)
        super().__init__(**kwargs)

    def _init_shelf(self, filename: str, remove_at_close: bool) -> None:
        self._filename = filename
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        self.remove_at_close = remove_at_close

        self.shelf = shelve.open(filename)

    def __getitem__(self, __k: str) -> Any:
        return self.shelf.__getitem__(__k)

    def __setitem__(self, __k: str, __v: Any) -> None:
        return self.shelf.__setitem__(__k, __v)

    def __len__(self) -> int:
        return self.shelf.__len__()

    def __delitem__(self, __k: str) -> None:
        return self.shelf.__delitem__(__k)

    def __iter__(self) -> Iterator[Any]:
        return self.shelf.__iter__()

    def _get_shelf_files(self) -> Iterable[str]:
        yield from glob.iglob(f"{self._filename}.*")

    def memory_footprint(self, key: Optional[str] = None) -> int:
        if key is None:
            return sum(os.path.getsize(savefile) for savefile in self._get_shelf_files())

        return super().memory_footprint(key)

    def close(self) -> None:
        if self.remove_at_close:
            for savefile in self._get_shelf_files():
                os.remove(savefile)
        else:
            self.shelf.close()


class HybridStorageProvider(StorageProvider):
    """
    HybridStorageProvider combines an in-memory storage approach and a
    persistent storage option.

    Memory Limit
    ------
    At creation, HybridStorageProvider can specify a `in_memory_limit`. Until
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
        "_in_memory_priority_queue",
        "_in_memory_limit",
        "_in_memory_storage",
        "_persistent_storage",
    )

    @property
    def _in_memory_footprint(self) -> int:
        return sum(self._in_memory_priority_queue.values())

    def __init__(
        self,
        __filename: str,
        __in_memory_limit: int = 1024 * 1024,
        __remove_at_close: bool = False,
        **kwargs: Any,
    ) -> None:
        self._init_in_memory_storage_provider(__in_memory_limit)
        self._init_persistent_memory_storage_provider(__filename, __remove_at_close)
        super().__init__(**kwargs)

    def _init_in_memory_storage_provider(self, in_memory_limit: int) -> None:
        self._in_memory_limit = in_memory_limit
        self._in_memory_priority_queue = maxpq()
        self._in_memory_storage = InMemoryStorageProvider()

    def _init_persistent_memory_storage_provider(
        self, filename: str, remove_at_close: bool
    ) -> None:
        self._persistent_storage = PersistentStorageProvider(filename, remove_at_close)

    def __getitem__(self, __k: str) -> Any:
        try:
            return self._in_memory_storage.__getitem__(__k)
        except KeyError:
            return self._persistent_storage.__getitem__(__k)

    def __len__(self) -> int:
        return self._in_memory_storage.__len__() + self._persistent_storage.__len__()

    def __iter__(self) -> Iterator[Any]:
        yield from self._in_memory_storage.__iter__()
        yield from self._persistent_storage.__iter__()

    def __delitem__(self, __k: str) -> None:
        try:
            self._in_memory_storage.__delitem__(__k)
            self._in_memory_priority_queue.__delitem__(__k)
        except KeyError:
            self._persistent_storage.__delitem__(__k)

    def __setitem__(self, __k: str, __v: Any) -> None:
        new_cost: int = asizeof.asizeof(__v)
        try:
            # stored in memory
            existing_cost: int = self._in_memory_priority_queue[__k]
            if new_cost != existing_cost:
                self._in_memory_priority_queue[__k] = new_cost
        except KeyError:
            self._in_memory_priority_queue[__k] = new_cost
        self._in_memory_storage.__setitem__(__k, __v)

        self._rebalance_memory()

    def _rebalance_memory(self) -> None:
        limit = self._in_memory_limit
        usage = self._in_memory_footprint
        while usage > limit:
            key, cost = self._in_memory_priority_queue.popitem()
            value = self._in_memory_storage.pop(key)
            self._persistent_storage.__setitem__(key, value)
            usage -= cost

    def memory_footprint(self, key: Optional[str] = None) -> int:
        if key is None:
            return (
                self._in_memory_storage.memory_footprint()
                + self._persistent_storage.memory_footprint()
            )
        return super().memory_footprint(key)

    def close(self) -> None:
        self._in_memory_storage.close()
        self._persistent_storage.close()
