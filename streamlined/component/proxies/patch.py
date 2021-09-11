from typing import Any, Type

from .proxy import Proxy


def patch(proxy_target: Any, patch_provider: Type[Any], **kwargs: Any) -> Type[Any]:
    class Patched(patch_provider, Proxy):
        def __init__(self, proxy_target, **kwargs: Any):
            super().__init__(proxy_target=proxy_target, **kwargs)

    return Patched(proxy_target, **kwargs)
