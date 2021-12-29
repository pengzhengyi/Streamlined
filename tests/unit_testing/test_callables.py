import os

import ray

from streamlined.common import AwaitCoroutine, RayAsyncActor, RayRemote, ShellActor


def test_ray_remote_on_function():
    @RayRemote()
    def add(a, b):
        return a + b

    assert ray.get(add(1, 2)) == 3

    @RayRemote.transform
    def sub(a, b):
        return a - b

    assert ray.get(sub(2, 1)) == 1


def test_ray_remote_on_callable():
    class Prefix:
        def __init__(self, prefix: str):
            self.prefix = prefix

        def __call__(self, string: str) -> str:
            return self.prefix + string

    prefix = Prefix("Hello")
    ray.get(RayRemote.transform(prefix)("John")) == "Hello John"


def test_await_coroutine():
    @AwaitCoroutine.transform
    async def add(a, b):
        return a + b

    assert add(1, 2) == 3


def test_ray_async_actor():
    @RayAsyncActor.transform
    async def add(a, b):
        return a + b

    assert ray.get(add.__call__.remote(1, 2)) == 3


def test_shell_actor_with_ray():
    Shell = ray.remote(ShellActor)
    pwd = Shell.remote("pwd")
    stdout, _ = ray.get(pwd.run_async.remote(encoding="utf-8"))
    assert stdout.strip() == os.getcwd()
