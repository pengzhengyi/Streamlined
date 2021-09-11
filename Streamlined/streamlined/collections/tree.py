from __future__ import annotations

from dataclasses import dataclass
from itertools import chain
from typing import Any, Generic, Iterable, List, Optional, TypeVar

T = TypeVar("T")


@dataclass
class TreeNode(Generic[T]):
    """
    A TreeNode is represents a node (more precisely, a subtree) in Tree structure.

    It encapsulates a `value` field to which unfound properties and methods will be proxied.
    """

    parent: Optional[TreeNode[Any]]
    value: T
    children: List[TreeNode[Any]]

    def __getattr__(self, name: str) -> Any:
        return getattr(self.value, name)

    def __str__(self) -> str:
        return self._format_subtree()

    def _format_self(self, indent_level: int = 0, fillchar: str = "\t") -> str:
        return fillchar * indent_level + str(self.value)

    def _format_subtree(self, indent_level: int = 0, fillchar: str = "\t") -> str:
        curent_node_str = self._format_self(indent_level, fillchar)
        return "\n".join(
            chain(
                [curent_node_str],
                (child._format_subtree(indent_level + 1) for child in self.children),
            )
        )

    def _format_ancestors(self, fillchar: str = "\t") -> str:
        ancestors_and_self = [self]
        ancestors_and_self.extend(self.ancestors())
        ancestors_and_self.reverse()

        return "\n".join(
            node._format_self(indent_level=index, fillchar=fillchar)
            for index, node in enumerate(ancestors_and_self)
        )

    def add_child(self, child: TreeNode[Any]) -> None:
        """Add a child node to current node"""
        self.children.append(child)
        child.parent = self

    def is_root(self) -> bool:
        """Whether a TreeNode is the root node (no parent) in Tree"""
        return self.parent is None

    def is_leaf(self) -> bool:
        """Whether a TreeNode is a leaf node (no children) in Tree"""
        return not bool(self.children)

    def ancestors(self) -> Iterable[TreeNode[Any]]:
        """Enumerate all ancestors of current node, starting from parent node of this node"""
        current_node = self.parent
        while current_node is not None:
            yield current_node
            current_node = current_node.parent


@dataclass
class Tree:
    """A tree structure where each node can have indeterminate number of child nodes."""

    root: TreeNode[Any]

    def __str__(self) -> str:
        return str(self.root)
