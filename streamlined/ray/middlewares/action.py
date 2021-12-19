from typing import Any

from ..common import IDENTITY_FACTORY, IS_NOT_CALLABLE, VALUE
from .middleware import Middleware, MiddlewareContext
from .parser import Parser


class Action(Parser, Middleware):
    @classmethod
    def verify(cls, value: Any) -> None:
        super().verify(value)

        if IS_NOT_CALLABLE(value):
            raise TypeError(f"{value} should be a callable")

    def _init_simplifications(self) -> None:
        super()._init_simplifications()

        self.simplifications.append((IS_NOT_CALLABLE, IDENTITY_FACTORY))

    def _do_parse(self, value):
        self.verify(value)

        return {"_action": value}

    async def _do_apply(self, context: MiddlewareContext):
        context.scoped.setmagic(VALUE, await context.executor.submit(self._action))
        await context.next()
        return context.scoped


ACTION = Action.get_name()
