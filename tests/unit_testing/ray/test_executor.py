from concurrent.futures import ProcessPoolExecutor
from itertools import repeat
from operator import add
from unittest.mock import Mock

from streamlined.ray.execution import Executable, Executor


def test_executor_with_simple_tasks():
    executor = Executor(executor=ProcessPoolExecutor())

    executables = [
        Executable.of(add, 1, 9),
        Executable.of(add, 2, 8),
        Executable.of(add, 3, 7),
    ]
    for future in executor.map(executables):
        assert future.result() == 10

    assert len(executor.executed) == 3
    assert len(executor.executing) == 0
