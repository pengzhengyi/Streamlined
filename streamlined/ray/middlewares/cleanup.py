from ..parsing import Simplification
from .action import Action
from .middleware import MiddlewareContext


class Cleanup(Action):
    def _init_simplifications(self) -> None:
        Simplification._init_simplifications(self)

    async def _do_apply(self, context: MiddlewareContext):
        await context.next()
        await context.executor.submit(self._action)
        return context.scoped


CLEANUP = Cleanup.get_name()
