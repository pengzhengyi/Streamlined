import os
from pathlib import Path

import pytest

from streamlined.services import (
    HybridStorageProvider,
    PersistentStorageOption,
    PersistentStorageProvider,
)


def test_persistent_storage_unpickleable(tmp_path: Path):
    unpickleable = (i for i in range(4))
    filename = str(tmp_path.joinpath("storage"))

    with PersistentStorageProvider.of(
        filename, PersistentStorageOption.PERSISTENT
    ) as storage_provider:
        with pytest.raises(TypeError):
            storage_provider["add"] = unpickleable


def test_hybrid_storage_handle_unpickleable(tmp_path: Path):
    unpickleable = (i for i in range(4))
    filename = str(tmp_path.joinpath("storage"))
    with HybridStorageProvider(filename, 1, True) as storage_provider:
        storage_provider["add"] = unpickleable
        assert len(storage_provider._storage) == 0


def test_update_for_hybrid_storage_provider(tmp_path: Path):
    unpickleable = (i for i in range(4))
    filename1 = str(tmp_path.joinpath("storage"))
    with HybridStorageProvider(filename1, 1, False) as storage_provider:
        storage_provider["add"] = unpickleable

        storage_provider.update(storage_provider)

        assert len(storage_provider) == 1


def test_pickle_io_file(tmp_path: Path):
    filepath = tmp_path.joinpath("foo.txt")
    file_writer = filepath.open("w", encoding="utf-8")
    file_writer.write("Hello World")
    file_writer.close()

    assert os.path.getsize(str(filepath)) > 0

    filename = str(tmp_path.joinpath("storage"))
    with HybridStorageProvider(filename, 1, False) as storage_provider:
        storage_provider["file_writer"] = file_writer

    assert os.path.getsize(str(filepath)) > 0
