import math
import urllib.request

import ray

from streamlined import ACTION, NAME, VALUE
from streamlined.component.runstep_component import RunstepComponent
from streamlined.utils import multiprocessing_map, remote, threading_map


def load_url(url, timeout: int = 60) -> int:
    """
    Retrieve a single page and report the status.
    """
    with urllib.request.urlopen(url, timeout=timeout) as conn:
        return conn.status


def test_threading_map_with_io() -> None:
    # using example on https://docs.python.org/3/library/concurrent.futures.html#processpoolexecutor
    URLS = ["http://www.foxnews.com/", "http://www.cnn.com/"]

    results = list(threading_map(load_url, URLS))
    assert all(result == 200 for result in results)


PRIMES = [
    112272535095293,
    112582705942171,
    112272535095293,
    115280095190773,
]


def is_prime(n) -> bool:
    """
    Tell whether a number is prime.
    """
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False

    sqrt_n = int(math.floor(math.sqrt(n)))
    for i in range(3, sqrt_n + 1, 2):
        if n % i == 0:
            return False
    return True


def test_multiprocessing_map() -> None:
    for result in multiprocessing_map(is_prime, PRIMES):
        assert result


def test_remote() -> None:
    action = lambda: 1
    assert ray.get(remote(action)) == 1


def test_multiprocessing_map_with_runstep_component(minimum_manager) -> None:
    # Setup
    config = {NAME: "check prime", ACTION: lambda: all(multiprocessing_map(is_prime, PRIMES))}
    component = RunstepComponent.of(config)
    assert component.execute(minimum_manager)
