import ray

from streamlined.ray.services import RayRemote, ray_remote


def test_ray_remote_on_function():
    @RayRemote()
    def add(a, b):
        return a + b

    assert ray.get(add(1, 2)) == 3

    @ray_remote
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
    ray.get(ray_remote(prefix)("John")) == "Hello John"
