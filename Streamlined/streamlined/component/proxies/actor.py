from typing import Any, Callable, Set, Type

import ray

from .patch import patch


class ActorPatch:
    """
    A patch for `ray.Actor` specifying a set of methods as remote.

    When calling these methods, it will automatically call that's remote function.
    For example, if `"foo"` is in remote_methods, then calling `actor.foo` will call
    `actor.foo.remote` under the hood.

    All other method names not in remote methods will be treated as synchronous methods.
    This is implemented by first exeucting its remote function and then wait on the result.

    [Actor](https://docs.ray.io/en/master/walkthrough.html?highlight=actor#remote-classes-actors)
    """

    def __init__(self, remote_methods: Set[str], **kwargs: Any):
        super().__init__(**kwargs)
        self._remote_methods = remote_methods

    def __getattr__(self, name: str) -> Any:
        attribute = getattr(self._proxy_target, name)
        if callable(attribute):
            if name in self._remote_methods:
                # execute as remote function
                return attribute.remote
            else:
                # execute as synchronous function
                return lambda *args, **kwargs: ray.get(attribute.remote(*args, **kwargs))
        else:
            return attribute


Actor: Callable[
    [ray.actor.ActorHandle, Set[str]], Type[Any]
] = lambda actor, remote_methods: patch(
    proxy_target=actor,
    patch_provider=ActorPatch,
    remote_methods=remote_methods,
)
