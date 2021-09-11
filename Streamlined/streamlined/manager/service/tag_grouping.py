from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Dict, Set

from .service import Service

if TYPE_CHECKING:
    from ...component import Component


class TagGrouping(Service):
    _tag_to_components: Dict[str, Set[Component]]
    _component_to_tags: Dict[Component, Set[str]]

    def __init__(self) -> None:
        super().__init__()
        self._tag_to_components = defaultdict(set)
        self._component_to_tags = defaultdict(set)

    def get_tags(self, component: Component) -> Set[str]:
        return self._component_to_tags[component]

    def get_components(self, tag: str) -> Set[Component]:
        return self._tag_to_components[tag]

    def set_tag(self, component: Component, tag: str):
        self._tag_to_components[tag].add(component)
        self._component_to_tags[component].add(tag)

    def has_tag(self, component: Component, tag: str) -> bool:
        return tag in self.get_tags(component)
