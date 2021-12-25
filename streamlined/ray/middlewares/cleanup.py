from ..parsing import Simplification
from .action import Action
from .middleware import Context


class Cleanup(Action):
    def _init_simplifications(self) -> None:
        Simplification._init_simplifications(self)

    async def _do_apply(self, context: Context):
        await context.next()
        await context.submit(self._action)
        return context.scoped


CLEANUP = Cleanup.get_name()
