from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Dict, Optional, Union

from ...collections import Tree, TreeNode
from .service import Service


class Scope:
    """A scope stores mappings from name to value"""

    _name_to_value: Dict[str, Any]

    def __init__(self) -> None:
        self._name_to_value = dict()

    def __str__(self) -> str:
        return str(self._name_to_value)

    @staticmethod
    def decorate_magic_value_name(name: str) -> str:
        """Differentiate special values by prefix and postfix its name by one underscore."""
        return f"_{name}_"

    def get_value(self, name: str) -> Any:
        """Retrieve a value under given name in current scope"""
        return self._name_to_value[name]

    def set_value(self, name: str, value: Any) -> None:
        """Register a value under given name in current scope"""
        self._name_to_value[name] = value

    def set_magic_value(self, name: str, value: Any) -> None:
        """
        Register a value under given name in current scope according
        to special naming indicated by `decorate_magic_value_name`.
        """
        self.set_value(name=self.decorate_magic_value_name(name), value=value)


class Scoping(Service):
    """Manage a tree of Scope"""

    _root: TreeNode[Scope]
    _calltree: Tree
    _head: TreeNode[Scope]

    def __init__(self) -> None:
        super().__init__()
        self._root = TreeNode(parent=None, value=Scope(), children=[])
        self._calltree = Tree(self._root)
        self._head = self._root

    def get_current_scope(self) -> TreeNode[Scope]:
        """Get the current scope. This is the newest added scope."""
        return self._head

    def get_global_scope(self) -> TreeNode[Scope]:
        """Get the global scope. This is the oldest added scope."""
        return self._root

    def _add_new_scope(self) -> TreeNode[Scope]:
        new_scope_node = TreeNode(parent=None, value=Scope(), children=[])
        self._head.add_child(new_scope_node)
        return new_scope_node

    def enter_new_scope(self) -> TreeNode[Scope]:
        """Create a new scope and set it as the current scope."""
        new_scope_node = self._add_new_scope()
        self._head = new_scope_node
        return new_scope_node

    def exit_current_scope(self) -> Optional[TreeNode[Scope]]:
        """Exit current scope and set the current scope to its parent."""
        if self._head.is_root():
            return None
        else:
            current_scope = self.get_current_scope()
            self._head = self._head.parent
            return current_scope

    @contextmanager
    def scoped(self) -> None:
        """Execute a block inside a new scope."""
        scope = self.enter_new_scope()

        try:
            yield scope
        finally:
            self.exit_current_scope()

    def get_value(self, name: str) -> Any:
        """Retrieve a value under given name, starting from current scope"""
        current_scope = self.get_current_scope()
        try:
            return current_scope.get_value(name)
        except KeyError:
            for ancestor in current_scope.ancestors():
                try:
                    return ancestor.get_value(name)
                except KeyError as key_error:
                    error = key_error
                    continue
            raise KeyError from error

    def set_global_value(self, name: str, value: Any) -> None:
        """
        Set a value at global scope.
        """
        return self.set_value(name, value, self.get_global_scope())

    def set_value(
        self, name: str, value: Any, scope: Optional[Union[Scope, TreeNode[Scope]]] = None
    ) -> None:
        """
        Set a value at given scope. When scope is not provided, it will default to current scope.
        """
        if scope is None:
            scope = self.get_current_scope()

        scope.set_value(name, value)

    def set_magic_value(
        self, name: str, value: Any, scope: Optional[Union[Scope, TreeNode[Scope]]] = None
    ) -> None:
        """
        Register a value under given name in given scope according
        to special naming rules. When scope is not provided, it will default to current scope.
        """
        if scope is None:
            scope = self.get_current_scope()

        scope.set_magic_value(name, value)
