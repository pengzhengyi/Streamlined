from __future__ import annotations

from collections import UserDict
from typing import Any, Iterator, MutableMapping, TypeVar

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
