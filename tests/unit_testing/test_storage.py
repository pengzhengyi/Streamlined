import os
import tracemalloc

from streamlined.services.storage import Dictionary, Shelf


def test_memory_reduction_of_shelf():
    tracemalloc.start()

    with Dictionary() as dictionary:
        for i in range(1000):
            dictionary[f"{i}"] = i
        _, dict_peak = tracemalloc.get_traced_memory()
    tracemalloc.reset_peak()
    del dictionary

    with Shelf() as shelf:
        for i in range(100):
            shelf[f"{i}"] = i
        _, shelf_peak = tracemalloc.get_traced_memory()
    tracemalloc.reset_peak()
    del shelf

    assert shelf_peak < dict_peak


def test_shelf_cleanup():
    with Shelf() as shelf:
        filepath = shelf._tempdir.name
        assert os.path.isdir(filepath)
    assert not os.path.isdir(filepath)
