from ..common import IDENTITY_FACTORY, IS_NOT_CALLABLE
from .middleware import Middleware
from .parser import Parser


class Action(Parser, Middleware):
    def _init_simplifications(self) -> None:
        super()._init_simplifications()

        self.simplifications.append((IS_NOT_CALLABLE, IDENTITY_FACTORY))

    def _do_parse(self, value):
        if IS_NOT_CALLABLE(value):
            raise TypeError(f"{value} should be a callable")
        else:
            return {"action": value}

    async def _do_apply(self, executor, next):
        await executor.submit(self._action)
        await next()


ACTION = Action.get_name()
