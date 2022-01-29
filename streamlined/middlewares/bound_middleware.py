from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..services import Scoped
from .context import Context

if TYPE_CHECKING:
    from .middleware import Middleware


@dataclass
class BoundMiddleware:
    middleware: Middleware
    context: Context

    async def apply_into(self) -> Scoped:
        return await self.middleware.apply_into(self.context)

    async def apply_onto(self) -> Scoped:
        return await self.middleware.apply_onto(self.context)
