from ..common import IS_CALLABLE, IS_NOT_CALLABLE, IS_NOT_STR
from .middleware import Middleware, MiddlewareContext
from .parser import Parser


class Name(Parser, Middleware):
    def _do_parse(self, value):
        if IS_NOT_CALLABLE(value) and IS_NOT_STR(value):
            raise TypeError(f"{value} should be either a callable or a string")
        else:
            return {"_name": value}

    async def get_register_name(self, executor) -> str:
        if IS_CALLABLE(name := self._name):
            return await executor.submit(name)
        else:
            return name

    async def _do_apply(self, context: MiddlewareContext):
        name = await self.get_register_name(context.executor)

        context.scoped.setmagic(NAME, name, num_scope_up=1)

        await context.next()
        return context.scoped


NAME = Name.get_name()
