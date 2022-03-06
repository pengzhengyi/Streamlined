from __future__ import annotations

from collections import UserDict
from typing import (
    Callable,
    Dict,
    Generic,
    MutableMapping,
    Sequence,
    Set,
    TypeVar,
    Union,
)

K = TypeVar("K")
V = TypeVar("V")


class Bag(UserDict[K, V]):
    """
    A bag is essentially a wrapper of `defaultdict(set)` with the following additional functionality:

    `self[key] = item` is equivalent to `self[key].add(item)`
    """

    __slots__ = ("data", "set_factory")

    def __init__(
        self,
        dict_factory: Callable[[], Dict[K, Set[V]]] = dict,
        set_factory: Callable[[], Set[V]] = set,
    ) -> None:
        self.data: Dict[K, Set[V]] = dict_factory()
        self.set_factory = set_factory

    def __setitem__(self, key: K, item: V) -> None:
        try:
            self.data[key].add(item)
        except KeyError:
            _set = self.set_factory()
            _set.add(item)
            self.data[key] = _set


IndexFactory = Callable[[], MutableMapping[K, Sequence[V]]]


class BidirectionalIndex(Generic[K, V]):
    """
    BidirectionalIndex has two indexing system: forward index and inverted index.

    For example, consider a list of documents. Forward index means finding the set of words from a document while inverted index means finding the set of documents containing that word.

    Notes
    --------
    Only __getitem__ and __setitem__ are implemented in this base class.
    Additional functionalities should be provided by subclasses.

    See Also
    --------
    [Inverted Index](https://en.wikipedia.org/wiki/Inverted_index)
    """

    __slots__ = ("data", "inverted_index")

    @property
    def forward_index(self) -> MutableMapping[K, Sequence[V]]:
        return self.data

    def __init__(
        self,
        forward_index_factory: IndexFactory[K, V] = Bag,
        inverted_index_factory: IndexFactory[V, K] = Bag,
    ) -> None:
        self.__init_index(forward_index_factory, inverted_index_factory)

    def __init_index(
        self,
        forward_index_factory: IndexFactory[K, V],
        inverted_index_factory: IndexFactory[V, K],
    ) -> None:
        self.data: MutableMapping[K, Sequence[V]] = forward_index_factory()
        self.inverted_index: MutableMapping[V, Sequence[K]] = inverted_index_factory()

    def __getitem__(self, key: Union[K, V]) -> Union[Sequence[V], Sequence[K]]:
        try:
            return self.forward_index[key]
        except KeyError:
            return self.inverted_index[key]

    def __setitem__(self, key: K, item: V) -> None:
        self.forward_index[key] = item
        self.inverted_index[item] = key
