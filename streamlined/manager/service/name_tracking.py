from __future__ import annotations

from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from ...component import Component

from .service import Service


class NameTracking(Service):
    _name_to_component: Dict[str, Component]
    _component_to_name: Dict[Component, str]

    def __init__(self):
        super().__init__()
        self._name_to_component = dict()
        self._component_to_name = dict()

    def get_name(self, component: Component) -> str:
        return self._component_to_name[component]

    def get_component(self, name: str) -> Component:
        return self._name_to_component[name]

    def set_name(self, name: str, component: Component):
        self._name_to_component[name] = component
        self._component_to_name[component] = name
