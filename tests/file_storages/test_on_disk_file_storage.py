import pathlib

import pytest

from lenzr_server.file_storages.file_storage import FileID
from lenzr_server.file_storages.on_disk_file_storage import OnDiskFileStorage


@pytest.fixture
def on_disk_file_storage(tmp_path):
    return OnDiskFileStorage(base_path=tmp_path)


def test__add_file__valid_metadata_and_content__file_is_written(on_disk_file_storage):
    file_id = FileID("test_file")
    content = b"test_content"
    on_disk_file_storage.add_file(file_id, content)

    expected_file_path = pathlib.Path(on_disk_file_storage._base_path) / "test_file"
    assert expected_file_path.exists()
    with open(expected_file_path, "rb") as f:
        assert f.read() == content


def test__get_file_content__valid_existing_file__returns_correct_content(on_disk_file_storage):
    file_id = FileID("test_file")
    content = b"test_content"
    on_disk_file_storage.add_file(file_id, content)

    retrieved_content = on_disk_file_storage.get_file_content(file_id)
    assert retrieved_content == content


def test__get_file_content__nonexistent_file__raises_file_not_found_error(on_disk_file_storage):
    file_id = FileID("nonexistent_file")

    with pytest.raises(FileNotFoundError):
        on_disk_file_storage.get_file_content(file_id)


@pytest.mark.parametrize(
    "file_id",
    [
        pytest.param("", id="empty"),
        pytest.param("..", id="parent_dir"),
        pytest.param("../escape", id="parent_traversal"),
        pytest.param("sub/file", id="forward_slash"),
        pytest.param("/etc/passwd", id="absolute_path"),
        pytest.param(".", id="current_dir"),
    ],
)
def test__add_file__rejects_traversal_attempts(on_disk_file_storage, file_id):
    with pytest.raises(ValueError):
        on_disk_file_storage.add_file(FileID(file_id), b"x")


def test__add_file__cannot_escape_base_path(on_disk_file_storage, tmp_path):
    sibling = tmp_path.parent / "sibling"
    sibling.mkdir(exist_ok=True)

    with pytest.raises(ValueError):
        on_disk_file_storage.add_file(FileID(".."), b"x")

    assert not (sibling / "x").exists()
