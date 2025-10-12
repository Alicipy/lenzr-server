import pathlib

import pytest

from lenzr_server.file_storages.on_disk_file_storage import (
    OnDiskFileStorage,
    OnDiskSearchParameters,
)


@pytest.fixture
def on_disk_file_storage(tmp_path):
    return OnDiskFileStorage(base_path=tmp_path)


def test__add_file__valid_metadata_and_content__file_is_written(on_disk_file_storage):
    search_params = OnDiskSearchParameters(on_disk_filename="test_file")
    content = b"test_content"
    on_disk_file_storage.add_file(search_params, content)

    expected_file_path = pathlib.Path(on_disk_file_storage._base_path) / "test_file"
    assert expected_file_path.exists()
    with open(expected_file_path, "rb") as f:
        assert f.read() == content


def test__get_file_content__valid_existing_file__returns_correct_content(on_disk_file_storage):
    search_params = OnDiskSearchParameters(on_disk_filename="test_file")
    content = b"test_content"
    on_disk_file_storage.add_file(search_params, content)

    retrieved_content = on_disk_file_storage.get_file_content(search_params)
    assert retrieved_content == content


def test__get_file_content__nonexistent_file__raises_file_not_found_error(on_disk_file_storage):
    search_params = OnDiskSearchParameters(on_disk_filename="nonexistent_file")

    with pytest.raises(FileNotFoundError):
        on_disk_file_storage.get_file_content(search_params)