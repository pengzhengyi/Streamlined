from concurrent.futures import ProcessPoolExecutor
from itertools import repeat
from operator import add
from unittest.mock import Mock

import ray

from streamlined.ray.execution import Executable, Executor, RayExecutor


def test_executor_with_simple_tasks():
    executor = Executor(executor=ProcessPoolExecutor())

    executables = [
        Executable(add, 1, 9),
        Executable(add, 2, 8),
        Executable(add, 3, 7),
    ]
    for future in executor.map(executables):
        assert future.result() == 10

    assert len(executor.executed) == 3
    assert len(executor.executing) == 0


def test_ray_executor_with_simple_arithmetic():
    def inc(a):
        return a + 1

    executor = RayExecutor()
    for objectref, result in zip(executor.map(inc, range(5)), range(1, 6)):
        assert ray.get(objectref) == result
