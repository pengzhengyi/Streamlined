from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Type

from ..capabilities import RunInNewScope
from .patch import patch

if TYPE_CHECKING:
    from ...manager.manager import Manager
    from .. import RunstepsComponent


class RunstepsComponentPatch(RunInNewScope):
    """
    A patched version of runsteps that will provide a runnable runsteps.
    """

    def __init__(self, manager: Manager, **kwargs: Any):
        run_action = lambda: self.execute(manager)
        super().__init__(manager, run_action, **kwargs)


RunstepsComponentProxy: Callable[
    [RunstepsComponent, Manager], Type[RunstepsComponent]
] = lambda runsteps_component, manager: patch(
    proxy_target=runsteps_component,
    patch_provider=RunstepsComponentPatch,
    manager=manager,
)
