import ray

from streamlined.component.proxies import Actor


@ray.remote
class Counter(object):
    def __init__(self):
        self.value = 0

    def increment(self):
        self.value += 1
        return self.value


def test_synchronous_method() -> None:
    counter = Counter.remote()
    actor = Actor(counter, set())
    assert actor.increment() == 1


def test_remote_method() -> None:
    counter = Counter.remote()
    actor = Actor(counter, set(["increment"]))
    assert ray.get(actor.increment()) == 1
