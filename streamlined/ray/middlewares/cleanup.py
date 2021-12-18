from ..parsing import Simplification
from .action import Action


class Cleanup(Action):
    def _init_simplifications(self) -> None:
        Simplification._init_simplifications(self)

    async def apply(self, executor, next):
        await next()
        await executor.submit(self._action)


CLEANUP = Cleanup.get_name()
