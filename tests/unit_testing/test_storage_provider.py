from pathlib import Path
from warnings import catch_warnings

import pytest

from streamlined.services import (
    HybridStorageProvider,
    PersistentStorageOption,
    PersistentStorageProvider,
)


def test_persistent_storage_unpickleable(tmp_path: Path):
    unpickleable = lambda a, b: a + b
    filename = str(tmp_path.joinpath("storage"))

    with PersistentStorageProvider.of(
        filename, PersistentStorageOption.PERSISTENT
    ) as storage_provider:
        with pytest.raises(AttributeError):
            storage_provider["add"] = unpickleable


def test_hybrid_storage_warning_for_unpickleable_exceeds_memory(tmp_path: Path):
    unpickleable = lambda a, b: a + b
    filename = str(tmp_path.joinpath("storage"))
    with HybridStorageProvider(filename, 1, True) as storage_provider:
        with catch_warnings(record=True) as w:
            storage_provider["add"] = unpickleable

            assert len(w) == 1
            assert issubclass(w[-1].category, RuntimeWarning)
