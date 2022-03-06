import os
import tracemalloc
from concurrent.futures import ProcessPoolExecutor
from uuid import uuid4

from streamlined.services.storage import Dictionary, Storage


def trace_memory(storage_provider):
    tracemalloc.start()
    with storage_provider() as storage:
        for i in range(1000):
            storage[f"{i}"] = uuid4()
        _, peak = tracemalloc.get_traced_memory()
    tracemalloc.reset_peak()
    del storage
    return peak


def test_memory_reduction_of_storage():
    with ProcessPoolExecutor() as executor:
        used_memory = list(executor.map(trace_memory, [Dictionary, Storage]))

    assert used_memory[1] < used_memory[0]


def test_shelf_cleanup():
    with Storage() as shelf:
        filepath = shelf._tempdir.name
        assert os.path.isdir(filepath)
    assert not os.path.isdir(filepath)
