from __future__ import annotations

from collections import UserDict
from contextlib import contextmanager
from typing import Any, Optional

from treelib import Node, Tree

from .service import Service


def to_magic_naming(name: str) -> str:
    """
    Transform a plain name to a magic name reserved for special variables.

    >>> to_magic_naming('value')
    '_value_'
    """
    return f"_{name}_"


class Scope(UserDict):
    """
    Scope stores mappings from name to value.
    """

    def setmagic(self, name: str, value: Any) -> None:
        """
        Similar to `self[name] = value` but applies magic nomenclature.

        >>> scope = Scope()
        >>> scope.setmagic('value', 3)
        >>> scope[to_magic_naming('value')]
        3
        """
        self[to_magic_naming(name)] = value


class Scoping(Service):
    """
    Scoping can be used as a calltree to track execution.

    This is because a tree can reflect the following two modes of execution:

    - caller-callee corresponds to parent-child relationship
    - parallel-execution corresponds to sibling relationship

    >>> scoping = Scoping()
    >>> scoping['x'] = 1
    >>> _ = scoping.create_scope(identifier='child', y=10)
    >>> scoping['x'] + scoping['y']
    11
    >>> scoping.exit_scope()
    True
    >>> 'x' in scoping
    True
    >>> 'y' in scoping
    False
    """

    def __init__(
        self,
        *args: Any,
        _tree: Optional[Tree] = None,
        _root_tag: Any = "global",
        _root_identifier: Any = "global",
        _head: Optional[Node] = None,
        **kwargs: Any,
    ):
        """
        The constructor can be invoked in two flavors:

        - Create New: provide `_root_tag` and `_root_identifier` if defaults aren't good
        - From Existing: provide `_tree` and optionally provide `_head`
        """
        super().__init__(*args, **kwargs)
        self.__init_tree(_root_tag, _root_identifier, _tree, _head)

    def __init_tree(
        self,
        _root_tag: Any,
        _root_identifier: Any,
        _tree: Optional[Tree] = None,
        _head: Optional[Node] = None,
    ):
        if _tree:
            # from existing
            self._tree = _tree
            self._root = self._tree[self._tree.root]
            self._head = _head if _head else self._root
        else:
            # create new
            self._tree = Tree()
            self._root = self._tree.create_node(
                tag=_root_tag, identifier=_root_identifier, data=Scope()
            )
            self._head = self._root

    @property
    def current_scope(self) -> Scope:
        return self._head.data

    @property
    def global_scope(self) -> Scope:
        return self._root.data

    def __getitem__(self, name: str) -> Any:
        try:
            identifier = next(
                self._tree.rsearch(self._head.identifier, filter=lambda node: name in node.data)
            )
            return self._tree[identifier].data[name]
        except StopIteration as error:
            raise KeyError from error

    def __contains__(self, name: str) -> bool:
        try:
            _ = self[name]
            return True
        except KeyError:
            return False

    def __setitem__(self, name: str, value: Any) -> None:
        self.current_scope[name] = value

    def setmagic(self, name: str, value: Any) -> None:
        self.current_scope.setmagic(name, value)

    def create_scope(self, tag: Any = None, identifier: Any = None, **mappings: Any) -> Scope:
        self._head = self._tree.create_node(
            tag=tag, identifier=identifier, parent=self._head, data=Scope(**mappings)
        )
        return self._head.data

    def exit_scope(self, identifier: Any = None, scope: Optional[Scope] = None) -> bool:
        """
        Exit a given scope. The current scope (head) will be set to its parent scope.

        The scope to exit can be specified either by identifier or reference.
        When both are supplied, identifier takes precedence.

        * The global (root) scope will not be exited.
        * In current implementation, the exited scope is still accessible in the scoping. But this behavior is not guaranteed.
        * When neither identifier nor scope are specified, current scope will be exited.

        :param identifier: Identifier of the scope.
        :param scope: A reference to the scope.
        :returns: True if specified scope is exited. False when it cannot be exited.
        :throws: When the specified scope cannot be found.
        """
        if scope is None:
            if identifier is None:
                identifier = self._head.identifier
            node = self._tree[identifier]
        else:
            if identifier is None:
                node = next(self._tree.filter_nodes(lambda node: node.data == scope))
                identifier = node.identifier
            else:
                # identifier takes precedence
                node = self._tree[identifier]

        if not node.is_root():
            self._head = self._tree.parent(identifier)
            return True

        return False

    @contextmanager
    def new_scope(self, tag: Any = None, identifier: Any = None, **mappings: Any) -> None:
        """Execute inside a new scope."""
        scope = self.create_scope(tag=tag, identifier=identifier, **mappings)

        try:
            yield scope
        finally:
            self.exit_scope(identifier=identifier)


if __name__ == "__main__":
    import doctest

    doctest.testmod()
