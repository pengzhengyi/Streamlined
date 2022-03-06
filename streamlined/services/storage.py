from __future__ import annotations

from collections import UserDict
from contextlib import suppress
from pickle import PickleError
from tempfile import TemporaryDirectory
from typing import Any, Iterator, MutableMapping, TypeVar
from weakref import finalize

from diskcache import Index

T = TypeVar("T")


class AbstractDictionary(MutableMapping[str, Any]):
    """
    AbstractDictionary is an abstract class providing functionalities of
    `dict` with string-based keys. This class implements `MutableMapping`
    interface.

    In essence, Dictionary represents a dict-like interface that support
    key value operations. This interface may be implemented through regular
    Python `dict` or a remote database.

    Besides functionalities of `dict`, Dictionary requires implementation
    of `close`. Based on `close` (by default, it calls `clear`), Dictionary
    can be used as a context manager which releases its memory/storage
    footprint.

    Memory Management
    ------
    To facilitate memory management, `AbstractDictionary` offers two methods

    + `clear` which is similar to `dict.clear` and should be used to reset
      dictionary state (remove all key value mappings).
    + `close` calls `clear` and does custom cleanup such that the
      dictionary's memory/storage footprint is released.

    `AbstractDictionary` can be used as context manager where `close` will
    be called at `__exit__`.

    `AbtractDictionary` comes with [finalizer](https://docs.python.org/3/library/weakref.html#weakref.finalize) which makes sure `close` is
    called before it is garbage collected.
    """

    __slots__ = ("__weakref__", "_is_closed", "_finalizer")

    def __init__(self) -> None:
        super().__init__()
        self._init_finalize()

    def _init_finalize(self) -> None:
        self._is_closed = False
        self._finalizer = finalize(self, self.close)

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

    def _clear(self) -> None:
        """
        ! should implement by derived classes to do actual clearing.
        """
        return

    def clear(self) -> None:
        """
        Offset the memory usage and restore the dictionary to starting state.

        ! Will delegate to `_clear` to do actual clearing.
        """
        if not self._is_closed:
            self._clear()

    def _close(self) -> None:
        """
        ! should implement by derived classes to do actual closing.
        """
        self.clear()

    def close(self) -> None:
        """
        Proper clean up. For example, make sure data is synced to storage/database.

        Once this function is called, reads/writes might not be supported.

        `close` is idempotent.

        ! Will delegate to `_close` to do actual clearing.
        """
        if not self._is_closed:
            self._close()
            self._is_closed = True


class Dictionary(UserDict[str, Any], AbstractDictionary):
    """
    Use a dictionary as a storage provider.
    """

    def __init__(self) -> None:
        super().__init__()
        AbstractDictionary.__init__(self)

    def _clear(self) -> None:
        AbstractDictionary._clear(self)
        self.data.clear()


class Storage(Index, AbstractDictionary):
    """
    Reference
    ------
    [Index](https://grantjenks.com/docs/diskcache/tutorial.html#index)
    """

    __slots__ = ("_tempdir",)

    def __init__(self) -> None:
        self._init_tempdir()
        Index.__init__(self, self._tempdir.name)
        AbstractDictionary.__init__(self)

    def _init_tempdir(self) -> None:
        self._tempdir = TemporaryDirectory(prefix="streamlined", suffix=self.__class__.__name__)

    def _close(self) -> None:
        self._tempdir.cleanup()


class Store(AbstractDictionary):
    """
    Store offers more extensible and flexible storage options.

    Mappings will be stored in Shelf (file-based storage) when supported
    and will be stored in memory otherwise.

    This allows potentially more key value mappings to be stored than
    the memory can fit.
    """

    __slots__ = (
        "_memory",
        "_storage",
    )

    def __init__(self) -> None:
        super().__init__()
        self._init_memory()
        self._init_storage()

    def _init_memory(self) -> None:
        self._memory = Dictionary()

    def _init_storage(self) -> None:
        self._storage = Storage()

    def __getitem__(self, __k: str) -> Any:
        with suppress(KeyError):
            return self._memory.__getitem__(__k)

        return self._storage.__getitem__(__k)

    def __contains__(self, __o: object) -> bool:
        return self._memory.__contains__(__o) or self._storage.__contains__(__o)

    def __len__(self) -> int:
        return self._memory.__len__() + self._storage.__len__()

    def __iter__(self) -> Iterator[Any]:
        yield from self._memory.__iter__()
        yield from self._storage.__iter__()

    def __delitem__(self, __k: str) -> None:
        with suppress(KeyError):
            self._memory.__delitem__(__k)

        self._storage.__delitem__(__k)

    def __setitem__(self, __k: str, __v: Any) -> None:
        try:
            self._storage.__setitem__(__k, __v)
        except (PickleError, AttributeError, TypeError):
            self._memory.__setitem__(__k, __v)

    def _clear(self) -> None:
        super()._clear()
        self._memory.clear()
        self._storage.clear()

    def close(self) -> None:
        super()._close()
        self._memory.close()
        self._storage.close()
