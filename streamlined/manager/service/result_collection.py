from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

from .service import Service

if TYPE_CHECKING:
    from ...component import Component


class ResultCollection(Service):
    _component_to_result: Dict[Component, Any]

    def __init__(self):
        super().__init__()
        self._component_to_result = dict()

    def set_result(self, component: Component, result: Any) -> None:
        self._component_to_result[component] = result

    def get_result(self, component: Component) -> Any:
        return self._component_to_result[component]
