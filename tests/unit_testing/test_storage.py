import tracemalloc
from pathlib import Path

from streamlined.services.storage import Dictionary, Shelf


def test_memory_reduction_of_shelf(tmp_path: Path):
    filepath = str(tmp_path.joinpath("foo.txt"))
    tracemalloc.start()

    with Dictionary() as dictionary:
        for i in range(1000):
            dictionary[f"{i}"] = i
        _, dict_peak = tracemalloc.get_traced_memory()
    tracemalloc.reset_peak()
    del dictionary

    with Shelf(filepath) as shelf:
        for i in range(100):
            shelf[f"{i}"] = i
        _, shelf_peak = tracemalloc.get_traced_memory()
    tracemalloc.reset_peak()
    del shelf

    assert shelf_peak < dict_peak
