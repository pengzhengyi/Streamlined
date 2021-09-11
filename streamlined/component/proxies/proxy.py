from typing import Any


class Proxy:
    def __init__(self, proxy_target: Any):
        super().__init__()
        self._set_target(proxy_target)

    def _set_target(self, proxy_target: Any):
        self._proxy_target = proxy_target
        self._proxy_target_type = type(proxy_target)

    def __getattr__(self, name: str) -> Any:
        attribute = getattr(self._proxy_target, name)
        if callable(attribute):
            # rebound self in methods to current instance so that properties in patch can
            # override same named properties in proxy target
            method = getattr(self._proxy_target_type, name)
            return lambda *args, **kwargs: method(self, *args, **kwargs)
        else:
            return attribute
