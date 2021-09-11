from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Iterable, Optional

from ...constants import TAGS
from .capability import Capability

if TYPE_CHECKING:
    from ...manager.manager import Manager
    from .name_capability import TName


class WithTag(Capability):
    """
    A mixin that allows tags to be added for a component.
    """

    TAGS_KEYNAME: ClassVar[str] = TAGS

    def __init__(self, tags: Optional[Iterable[str]] = None, **kwargs: Any):
        super().__init__(**kwargs)
        self._tags = tags if tags else []

    def __register_tag(self, tag: str, manager: Manager) -> None:
        manager.set_tag(tag=tag, component=self)
        manager.set_magic_value(name=self.TAGS_KEYNAME, value=tag)

    def __register_tags(self, tags: Iterable[str], manager: Manager) -> None:
        for tag in tags:
            self.__register_tag(tag, manager)

    def _execute_for_tags(self, manager: Manager) -> Iterable[str]:
        tags = self._tags
        if tags:
            self.__register_tags(tags, manager)
        return tags
