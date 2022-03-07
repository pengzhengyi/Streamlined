from __future__ import annotations

import uuid
from collections import deque
from contextlib import suppress
from typing import Any, Deque, Dict, Iterable, Iterator, Optional, Tuple, TypeVar, Union
from weakref import ReferenceType, ref

import networkx as nx
from pqdict import maxpq
from treelib import Node, Tree
from treelib.exceptions import MultipleRootError

from ..common import to_networkx, transplant
from ..common import update as tree_update
from .storage import AbstractDictionary, Store

K = TypeVar("K")
V = TypeVar("V")


def to_magic_naming(name: str) -> str:
    """
    Transform a plain name to a magic name reserved for special variables.

    >>> to_magic_naming('value')
    '_value_'
    """
    return f"_{name}_"


class Scope(Store):
    """
    Scope stores mappings from name to value.

    Scope can will utilize file-based store to reduce memory usage and therefore
    storing more mappings.

    Temporary Directory
    ------
    See [gettempdir](https://docs.python.org/3/library/tempfile.html#tempfile.gettempdir) for how temporary directory is determined from environment variables.

    See [tempdir](https://docs.python.org/3/library/tempfile.html#tempfile.tempdir)
    for how to change temporary directory to a custom location.
    """

    __slots__ = ("id",)
    __hash__ = object.__hash__

    @property
    def representation(self) -> str:
        return self.__str__()

    def __init__(self, _id: Optional[uuid.UUID] = None, **kwargs: Any) -> None:
        self._init_id(_id)
        super().__init__()
        self.update(**kwargs)

    def _init_id(self, _id: Optional[uuid.UUID] = None) -> None:
        if _id is None:
            _id = uuid.uuid4()

        self.id = _id

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


class ScopeRef(ref):
    @property
    def representation(self) -> str:
        scope: Optional[Scope] = self.__call__()
        if scope is not None:
            return scope.representation
        else:
            return "???"


class Scoping(AbstractDictionary):
    """
    Scoping can be used as a calltree to track execution.

    This is because a tree can reflect the following two modes of execution:

    - caller-callee corresponds to parent-child relationship
    - parallel-execution corresponds to sibling relationship
    """

    __slots__ = "_tree"

    @staticmethod
    def _get_scope(node: Node) -> Scope:
        data = node.data
        if isinstance(data, ReferenceType):
            return data()
        elif isinstance(data, Scope):
            return data
        else:
            raise TypeError(f"{data} is not type Scope")

    @staticmethod
    def _are_equal_node(scope_node: Node, other_scope_node: Node) -> bool:
        if scope_node is other_scope_node:
            return True
        return scope_node.identifier == other_scope_node.identifier

    @classmethod
    def _update_node_when_equal(cls, scope_node: Node, other_scope_node: Node) -> None:
        cls._get_scope(scope_node).update(cls._get_scope(other_scope_node))

    @property
    def global_scope(self) -> Scope:
        scope_id = self._tree.root
        return self._get_scope(self._tree[scope_id])

    @property
    def all_scopes(self) -> Iterable[Scope]:
        for node in self._tree.all_nodes_itr():
            yield self._get_scope(node)

    def __init__(self, _tree: Optional[Tree] = None):
        """
        The constructor can be invoked in two flavors:

        - Create New: call with no arguments
        - From Existing: provide `_tree`
        """
        super().__init__()
        self._init_tree(_tree)

    def __contains__(self, value: Any) -> bool:
        if isinstance(value, Scope):
            return self._tree.contains(value.id)
        else:
            return any(value in scope for scope in self.all_scopes)

    def __getitem__(self, name: Any) -> Any:
        return self.search(name, scope=self.global_scope)

    def __len__(self) -> int:
        return sum(len(scope) for scope in self.all_scopes)

    def __iter__(self) -> Iterator[Any]:
        for scope in self.descendants_scopes(self.global_scope, breadth_first=True):
            yield from scope

    def _init_tree(self, _tree: Optional[Tree] = None) -> None:
        if _tree is None:
            # create new
            self._tree = Tree()
            scope = self._create_scope()
            self._tree.create_node(identifier=scope.id, data=scope)
        else:
            # from existing
            self._tree = _tree

    def _clear(self) -> None:
        super()._clear()
        for scope in self.all_scopes:
            if scope is not None:
                # safeguard for finalizing
                scope.clear()

    def _ancestors(self, scope: Scope, start_at_root: bool = False) -> Iterable[Node]:
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

    def _descendants(self, scope: Scope, breadth_first: bool = True) -> Iterable[Node]:
        """
        Get descendants of a specified node.

        When `breadth_first` is True, descendant nodes will be yielded in breadth first
        order. Otherwise, it will be yielded in depth first order.

        For example, when
        A ──┬── B ──── C
            └── D ──── E

        Calling descendants on `A` with `breadth_first` being True will yield `A`, `B`,
        `D`, `C`, `E`. Otherwise, it will yield `A`, `B`, `C`, `D`, `E`.
        """
        descendants: Deque[Node] = deque([self._get_node(scope)])

        with suppress(IndexError):
            while node := descendants.popleft():
                yield node
                children = self._tree.children(node.identifier)
                if breadth_first:
                    descendants.extend(children)
                else:
                    descendants.extendleft(children)

    def enclosing_scopes(self, scope: Scope, start_at_root: bool = False) -> Iterable[Scope]:
        for node in self._ancestors(scope, start_at_root):
            yield self._get_scope(node)

    def descendants_scopes(self, scope: Scope, breadth_first: bool = True) -> Iterable[Scope]:
        for node in self._descendants(scope, breadth_first=breadth_first):
            yield self._get_scope(node)

    def _get_node(self, scope: Scope) -> Node:
        return self._tree[scope.id]

    def get(self, name: Any, scope: Scope) -> Any:
        """
        Find value of a specified name from a scope and its enclosing
        scopes.
        """
        for scope in self.enclosing_scopes(scope):
            try:
                return scope[name]
            except KeyError:
                continue
        raise KeyError(f"{name} is not in ancestors of {scope}")

    def getmagic(self, name: Any, scope: Scope) -> Any:
        """
        Find value of a specified name in magic naming from a scope and
        its enclosing scopes.
        """
        return self.get(to_magic_naming(name), scope)

    def search(self, name: Any, scope: Optional[Scope] = None) -> Any:
        """
        Find value of a specified name from a scope and its descendants
        scopes.

        When `scope` is not specified, default to global scope.
        """
        if scope is None:
            scope = self.global_scope

        for scope in self.descendants_scopes(scope):
            try:
                return scope[name]
            except KeyError:
                continue
        raise KeyError(f"{name} is not in descendants of {scope}")

    def searchmagic(self, name: Any, scope: Optional[Scope] = None) -> Any:
        """
        Find value of a specified name in magic naming from a scope and
        its enclosing scopes.

        When `scope` is not specified, default to global scope.
        """
        return self.search(to_magic_naming(name), scope)

    def update(self, scoping: Scoping) -> None:
        """
        Assume two scoping have same root node, `update` will merge in the changes introduced in the other tree.

        ! This operation is destructive, the other tree will become not useable.
        """
        tree_update(
            self._tree,
            scoping._tree,
            are_equal=self._are_equal_node,
            update_equal=self._update_node_when_equal,
        )

    def _create_scope(self, **kwargs: Any) -> Scope:
        return Scope(None, **kwargs)

    def add_scope(self, parent_scope: Scope, scope: Scope) -> Node:
        return self._tree.create_node(identifier=scope.id, data=scope, parent=parent_scope.id)

    def create_scope(self, parent_scope: Scope, **kwargs: Any) -> Scope:
        scope = self._create_scope(**kwargs)
        self.add_scope(parent_scope, scope)
        return scope

    def create_scoped(self, parent_scope: Scope, **kwargs: Any) -> Scoped:
        scope = self.create_scope(parent_scope, **kwargs)
        return Scoped(self, scope)

    def show(self, data_property: str = "representation", **kwargs: Any) -> None:
        """
        Print the tree structure in hierarchy style.

        Reference
        ------
        [Tree.show](https://treelib.readthedocs.io/en/latest/treelib.html#treelib.tree.Tree.show)
        """
        self._tree.show(data_property=data_property, **kwargs)

    def to_networkx(self) -> nx.DiGraph:
        """
        Convert a Tree to NetworkX DiGraph.
        """
        return to_networkx(self._tree, node_converter=self._get_scope)

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

    def write_dot(self, filename: str) -> None:
        """
        Write NetworkX graph G to Graphviz dot format on path.

        Path can be a string or a file handle.

        Reference
        ------
        [write_dot](https://networkx.org/documentation/stable/reference/generated/networkx.drawing.nx_pydot.write_dot.html)
        """
        graph = self.to_networkx()
        nx.drawing.nx_pydot.write_dot(graph, filename)


class Scoped(Scoping):
    """
    While Scoping is a tree of Scope, Scoped is a branch of Scope.
    """

    __slots__ = ("current_scope",)

    def __init__(self, scoping: Scoping, scope: Scope):
        super().__init__(Tree())
        self.__init_branch(scoping, scope)

    def __init_branch(self, scoping: Scoping, scope: Scope) -> None:
        self.current_scope = scope

        parent = None
        for node in scoping._ancestors(self.current_scope, start_at_root=True):
            scope = self._get_scope(node)
            with suppress(TypeError):
                scope = ScopeRef(scope)

            parent = self._tree.create_node(identifier=node.identifier, data=scope, parent=parent)

    def __getitem__(self, name: Any) -> Any:
        return self.get(name, scope=self.current_scope)

    def __setitem__(self, name: Any, value: Any) -> None:
        self.current_scope[name] = value

    def __contains__(self, name: Any) -> bool:
        return any(
            scope.__contains__(name) for scope in self.enclosing_scopes(start_at_root=False)
        )

    def __delitem__(self, __k: str) -> None:
        for scope in self.enclosing_scopes(start_at_root=False):
            if scope.__contains__(__k):
                scope.__delitem__(__k)
                return
        raise KeyError(f"{__k} can not be deleted")

    def __iter__(self) -> Iterator[Any]:
        for scope in self.enclosing_scopes(start_at_root=True):
            yield from scope

    def _ancestors(
        self, scope: Optional[Scope] = None, start_at_root: bool = False
    ) -> Iterable[Node]:
        if scope is None:
            scope = self.current_scope
        return super()._ancestors(scope, start_at_root=start_at_root)

    def _descendants(
        self, scope: Optional[Scope] = None, breadth_first: bool = True
    ) -> Iterable[Node]:
        if scope is None:
            scope = self.current_scope
        return super()._descendants(scope, breadth_first)

    def enclosing_scopes(
        self, scope: Optional[Scope] = None, start_at_root: bool = False
    ) -> Iterable[Scope]:
        if scope is None:
            scope = self.current_scope
        return super().enclosing_scopes(scope, start_at_root=start_at_root)

    def descendants_scopes(
        self, scope: Optional[Scope] = None, breadth_first: bool = True
    ) -> Iterable[Scope]:
        if scope is None:
            scope = self.current_scope
        return super().descendants_scopes(scope, breadth_first)

    def up(self, num_scope_up: int = 0) -> Scope:
        i = 0
        for i, scope in enumerate(self.enclosing_scopes()):
            if i == num_scope_up:
                return scope
        raise ValueError(f"{i+1} exceeds maximum tree depth")

    def get(self, name: Any, scope: Optional[Scope] = None) -> Any:
        """
        Find value of a specified name from a scope and its enclosing
        scopes.

        When `scope` is not specified, default to current scope.
        """
        if scope is None:
            scope = self.current_scope

        return super().get(name, scope)

    def getmagic(self, name: Any, scope: Optional[Scope] = None) -> Any:
        """
        Find value of a specified name in magic naming from a scope and
        its enclosing scopes.

        When `scope` is not specified, default to current scope.
        """
        if scope is None:
            scope = self.current_scope

        return super().getmagic(name, scope)

    def search(self, name: Any, scope: Optional[Scope] = None) -> Any:
        """
        Find value of a specified name from a scope and its descendants
        scopes.

        When `scope` is not specified, default to current scope.
        """
        if scope is None:
            scope = self.current_scope

        return super().search(name, scope)

    def searchmagic(self, name: Any, scope: Optional[Scope] = None) -> Any:
        """
        Find value of a specified name in magic naming from a scope and
        its enclosing scopes.

        When `scope` is not specified, default to current scope.
        """
        if scope is None:
            scope = self.current_scope

        return super().searchmagic(name, scope)

    def set(self, name: Any, value: Any, at: Union[str, int] = 0) -> None:
        if isinstance(at, int):
            scope = self.up(at)
        else:
            keyname = to_magic_naming(at + "_id")
            scope = self.arg_get(keyname)
        scope[name] = value

    def setmagic(self, name: Any, value: Any, at: Union[str, int] = 0) -> None:
        self.set(to_magic_naming(name), value, at)

    def arg_get(self, name: Any) -> Scope:
        """
        Return the nearest scope containing the name.
        """
        for scope in self.enclosing_scopes():
            if name in scope:
                return scope
        raise KeyError(f"Cannot find {name} in any enclosing scope of {self.current_scope}")

    def change(self, name: Any, value: Any) -> None:
        """
        Set a value at nearest enclosing scope containing this name.
        """
        scope = self.arg_get(name)
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
