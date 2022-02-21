from __future__ import annotations

import math
import os
import tempfile
import uuid
from collections import deque
from typing import Any, Deque, Dict, Iterable, Optional, Tuple, TypeVar, Union

import networkx as nx
from pqdict import maxpq
from treelib import Node, Tree
from treelib.exceptions import MultipleRootError

from ..common import to_networkx, transplant
from ..common import update as tree_update
from .storage_option import HybridStorageOption
from .storage_provider import HybridStorageProvider

K = TypeVar("K")
V = TypeVar("V")


def to_magic_naming(name: str) -> str:
    """
    Transform a plain name to a magic name reserved for special variables.

    >>> to_magic_naming('value')
    '_value_'
    """
    return f"_{name}_"


class Scope(HybridStorageProvider):
    """
    Scope stores mappings from name to value.
    """

    __slots__ = ("id",)

    __hash__ = object.__hash__

    @classmethod
    def of(
        cls,
        storage_option: HybridStorageOption = HybridStorageOption.TRANSIENT_MEMORY,
    ) -> Scope:
        """
        Create a Scope based on a storage type.
        """
        return cls(None, *storage_option.args, **storage_option.kwargs)

    def __init__(
        self,
        id: Optional[uuid.UUID] = None,
        memory_limit: Union[float, int] = math.inf,
        cleanup_at_close: bool = False,
        **kwargs: Any,
    ) -> None:
        self._init_id(id)
        super().__init__(
            self._get_default_persistent_storage_filename(),
            memory_limit,
            cleanup_at_close,
        )
        self.update(**kwargs)

    def _init_id(self, id: Optional[uuid.UUID]) -> None:
        if id is None:
            self.id = uuid.uuid4()
        else:
            self.id = id

    def _get_default_persistent_storage_filename(self) -> str:
        return os.path.join(tempfile.gettempdir(), "streamlined", "scoping", str(self.id))

    def __get_items_str(self) -> str:
        return ", ".join("{!s}={!r}".format(key, value) for key, value in self.items())

    def __get_abbreviated_items(self, limit: int) -> Iterable[Tuple[str, str]]:
        item_representations = maxpq()

        usage = 0
        for key, value in self.items():
            representation = repr(value)
            abbreviated_representation = f"<{type(value).__name__}>"
            cost = len(representation)
            item_representations.additem(
                (str(key), representation, abbreviated_representation), cost
            )
            usage += cost

        while usage > limit and item_representations:
            (
                (key, representation, abbreviated_representation),
                cost,
            ) = item_representations.popitem()

            deduction = cost - len(abbreviated_representation)
            usage -= deduction
            yield key, abbreviated_representation

        for key, representation, _ in item_representations.keys():
            yield key, representation

    def __get_abbreviated_items_str(self, limit: int = 1000) -> str:
        return ", ".join(f"{key}={value}" for key, value in self.__get_abbreviated_items(limit))

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({repr(self.id)}, {self.__get_abbreviated_items_str()})"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({repr(self.id)}, {self.__get_items_str()})"

    def __lt__(self, other: Scope) -> bool:
        return self.id < other.id

    def getmagic(self, name: str) -> Any:
        return self.__getitem__(to_magic_naming(name))

    def setmagic(self, name: str, value: Any) -> None:
        """
        Similar to `self[name] = value` but applies magic nomenclature.

        >>> scope = Scope()
        >>> scope.setmagic('value', 3)
        >>> scope[to_magic_naming('value')]
        3
        """
        self.__setitem__(to_magic_naming(name), value)


class Scoping:
    """
    Scoping can be used as a calltree to track execution.

    This is because a tree can reflect the following two modes of execution:

    - caller-callee corresponds to parent-child relationship
    - parallel-execution corresponds to sibling relationship
    """

    __slots__ = ("_tree", "_memory_limit", "_cleanup_at_close")

    @staticmethod
    def _are_equal_node(scope_node: Node, other_scope_node: Node) -> bool:
        if scope_node is other_scope_node:
            return True
        scope: Scope = scope_node.identifier
        other_scope: Scope = other_scope_node.identifier
        if scope is other_scope:
            return True

        return scope.id == other_scope.id

    @staticmethod
    def _update_node_when_equal(scope_node: Node, other_scope_node: Node) -> None:
        scope_node.identifier.update(other_scope_node.identifier)

    @classmethod
    def of(
        cls, storage_option: HybridStorageOption = HybridStorageOption.TRANSIENT_MEMORY
    ) -> Scoping:
        """
        Create a Scoping based on a storage type.
        """
        return cls(None, *storage_option.args, **storage_option.kwargs)

    @property
    def global_scope(self) -> Scope:
        return self._tree.root

    @property
    def all_scopes(self) -> Iterable[Scope]:
        for node in self._tree.all_nodes_itr():
            yield node.identifier

    def __init__(
        self,
        _tree: Optional[Tree] = None,
        memory_limit: Union[float, int] = math.inf,
        cleanup_at_close: bool = False,
    ):
        """
        The constructor can be invoked in two flavors:

        - Create New: call with no arguments
        - From Existing: provide `_tree`

        `memory_limit` can control how Scope chooses between saving object in memory
        versus storage. See `HybridStorageProvider` for more info.
        """
        self._init_tree(_tree)
        self._init_scope_init_args(memory_limit, cleanup_at_close)

    def __enter__(self) -> Scoping:
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.close()

    def _init_tree(self, _tree: Optional[Tree] = None) -> None:
        if _tree is None:
            # create new
            self._tree = Tree()
            self._tree.create_node(identifier=Scope())
        else:
            # from existing
            self._tree = _tree

    def _init_scope_init_args(
        self, memory_limit: Union[float, int], cleanup_at_close: bool
    ) -> None:
        self._memory_limit = memory_limit
        self._cleanup_at_close = cleanup_at_close

    def __contains__(self, scope: Scope) -> bool:
        return self._tree.contains(scope)

    def ancestors(self, scope: Scope, start_at_root: bool = False) -> Iterable[Node]:
        """
        Get ancestors of a specified node.

        If `start_at_root` is True, then the ancestors will be enumerated from root.
        Otherwise, they will be enumerated from specified node.

        For example, when `A -> B -> C`, calling `ancestors` on `C` will return
        [C, B, A] and [A, B, C] when `start_at_root` is set to True.
        """
        if start_at_root:
            ancestors: Deque[Node] = deque()

        node = self._get_node(scope)
        while node is not None:
            if start_at_root:
                ancestors.appendleft(node)
            else:
                yield node
            node = self._tree.parent(node.identifier)

        if start_at_root:
            yield from ancestors

    def enclosing_scopes(self, scope: Scope, start_at_root: bool = False) -> Iterable[Scope]:
        for node in self.ancestors(scope, start_at_root):
            yield node.identifier

    def _get_node(self, scope: Scope) -> Node:
        return self._tree[scope]

    def get(self, name: Any, scope: Scope) -> Any:
        for scope in self.enclosing_scopes(scope):
            try:
                return scope[name]
            except KeyError:
                continue
        raise KeyError(f"{name} is not in ancestors of {scope}")

    def update(self, scoping: Scoping) -> None:
        """
        Assume two scoping have same root node, `update` will merge in the changes introduced in the other tree.
        """
        tree_update(
            self._tree,
            scoping._tree,
            are_equal=self._are_equal_node,
            update_equal=self._update_node_when_equal,
        )

    def add_scope(self, parent_scope: Scope, scope: Scope) -> Node:
        return self._tree.create_node(identifier=scope, parent=parent_scope)

    def create_scope(self, parent_scope: Scope, **kwargs: Any) -> Scope:
        scope = Scope(None, self._memory_limit, self._cleanup_at_close, **kwargs)
        self.add_scope(parent_scope, scope)
        return scope

    def create_scoped(self, parent_scope: Scope, **kwargs: Any) -> Scoped:
        scope = self.create_scope(parent_scope, **kwargs)
        return Scoped(self, scope)

    def cleanup(self) -> None:
        """
        Forcing release of memory used for scopes.

        It will call `close` on every scope.
        """
        for scope in self.all_scopes:
            scope.cleanup()

    def close(self) -> None:
        """
        Proper clean up. It will call `close` on every scope.
        """
        for scope in self.all_scopes:
            scope.close()

    def show(self, **kwargs: Any) -> None:
        """
        Print the tree structure in hierarchy style.

        Reference
        ------
        [Tree.show](https://treelib.readthedocs.io/en/latest/treelib.html#treelib.tree.Tree.show)
        """
        self._tree.show(**kwargs)

    def to_networkx(self) -> nx.DiGraph:
        """
        Convert a Tree to NetworkX DiGraph.
        """
        return to_networkx(self._tree)

    def draw(
        self,
        pos: Optional[Dict[Any, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """
        Draw schedule using Matplotlib

        Tricks
        ------
        Use `bbox=dict(fc="white")` to only print labels.

        Reference
        ------
        [NetworkX draw_networkx](https://networkx.org/documentation/stable/reference/generated/networkx.drawing.nx_pylab.draw_networkx.html#networkx-drawing-nx-pylab-draw-networkx)
        """
        graph = self.to_networkx()
        if pos is None:
            pos = nx.nx_pydot.pydot_layout(graph, prog="dot", root=self.global_scope)

        nx.draw_networkx(
            graph,
            pos=pos,
            **kwargs,
        )

    def write_dot(self, filename: str, shape: str = "ellipsis", **kwargs: Any) -> None:
        """
        Write NetworkX graph G to Graphviz dot format on path.

        Path can be a string or a file handle.

        Reference
        ------
        [to_graphviz](https://treelib.readthedocs.io/en/latest/treelib.html#treelib.tree.Tree.to_graphviz)
        """
        self._tree.to_graphviz(filename, shape=shape)


class Scoped(Scoping):
    """
    While Scoping is a tree of Scope, Scoped is a branch of Scope.
    """

    __slots__ = ("current_scope",)

    def __init__(
        self,
        scoping: Scoping,
        scope: Scope,
    ):
        super().__init__(_tree=Tree())
        self.__init_branch(scoping, scope)

    def __init_branch(self, scoping: Scoping, scope: Scope) -> None:
        self.current_scope = scope

        parent = None
        for node in scoping.ancestors(self.current_scope, start_at_root=True):
            parent = self._tree.create_node(identifier=node.identifier, parent=parent)

    def __getitem__(self, name: Any) -> Any:
        return self.get(name, scope=self.current_scope)

    def __contains__(self, name: Any) -> bool:
        try:
            self.__getitem__(name)
            return True
        except KeyError:
            return False

    def __setitem__(self, name: Any, value: Any) -> None:
        self.current_scope[name] = value

    def __iter__(self) -> Iterable[Scope]:
        yield from self.enclosing_scopes(start_at_root=True)

    def ancestors(
        self, scope: Optional[Scope] = None, start_at_root: bool = False
    ) -> Iterable[Node]:
        if scope is None:
            scope = self.current_scope
        return super().ancestors(scope, start_at_root=start_at_root)

    def enclosing_scopes(
        self, scope: Optional[Scope] = None, start_at_root: bool = False
    ) -> Iterable[Scope]:
        if scope is None:
            scope = self.current_scope
        return super().enclosing_scopes(scope, start_at_root=start_at_root)

    def up(self, num_scope_up: int = 0) -> Scope:
        i = 0
        for i, scope in enumerate(self.enclosing_scopes()):
            if i == num_scope_up:
                return scope
        raise ValueError(f"{i+1} exceeds maximum tree depth")

    def get(self, name: Any, scope: Optional[Scope] = None) -> Any:
        if scope is None:
            scope = self.current_scope

        return super().get(name, scope)

    def getmagic(self, name: Any) -> Any:
        return self[to_magic_naming(name)]

    def set(self, name: Any, value: Any, at: Union[str, int] = 0) -> None:
        if isinstance(at, int):
            scope = self.up(at)
        else:
            keyname = to_magic_naming(at + "_id")
            scope = self.get_nearest(keyname)
        scope[name] = value

    def setmagic(self, name: Any, value: Any, at: Union[str, int] = 0) -> None:
        self.set(to_magic_naming(name), value, at)

    def get_nearest(self, name: Any) -> Scope:
        """
        Return the nearest scope containing the name.
        """
        for scope in self.enclosing_scopes():
            if name in scope:
                return scope
        raise KeyError(f"Cannot find {name} in any enclosing scope of {self.current_scope}")

    def set_nearest(self, name: Any, value: Any) -> None:
        """
        Set a value at nearest enclosing scope containing this name.
        """
        scope = self.get_nearest(name)
        scope[name] = value

    def update(self, scoped: Scoping) -> None:
        """
        When provided scoped have same global scope, `update` will merge in the
        changes.

        Otherwise, provided scoped will be copied as a whole as descendants
        of current scope.
        """
        try:
            super().update(scoped)
        except MultipleRootError:
            transplant(
                self._tree,
                self._get_node(self.current_scope),
                scoped._tree,
                scoped._get_node(scoped.global_scope),
            )

    def create_scope(self, parent_scope: Optional[Scope] = None, **kwargs: Any) -> Scope:
        if parent_scope is None:
            parent_scope = self.current_scope
        return super().create_scope(parent_scope, **kwargs)

    def create_scoped(self, parent_scope: Optional[Scope] = None, **kwargs: Any) -> Scoped:
        if parent_scope is None:
            parent_scope = self.current_scope
        return super().create_scoped(parent_scope, **kwargs)


if __name__ == "__main__":
    import doctest

    doctest.testmod()
