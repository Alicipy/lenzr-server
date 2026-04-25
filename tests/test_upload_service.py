import os
from unittest.mock import MagicMock

import pytest
from sqlmodel import select

from lenzr_server.file_storages.on_disk_file_storage import OnDiskFileStorage
from lenzr_server.models.uploads import UploadMetaData
from lenzr_server.upload_id_creators.hashing_id_creator import HashingIDCreator
from lenzr_server.upload_service import (
    UploadAlreadyExistingException,
    UploadNotFoundException,
    UploadService,
)


@pytest.fixture
def file_storage(tmp_path):
    yield OnDiskFileStorage(tmp_path)


@pytest.fixture
def id_creator():
    return HashingIDCreator(0)


@pytest.fixture
def upload_service(database_session, file_storage, id_creator):
    return UploadService(file_storage, database_session, id_creator)


def test__add_upload__valid_data__stores_in_database_and_disk(
    upload_service, database_session, file_storage
):
    content = b"test_content"
    content_type = "text/plain"

    upload = upload_service.add_upload(content, content_type)

    # Verify database entry
    result = database_session.exec(
        select(UploadMetaData).where(UploadMetaData.upload_id == upload.upload_id)
    ).first()
    assert result is not None
    assert result == upload
    assert result.content_type == content_type

    # Verify file storage
    file_path = os.path.join(file_storage._base_path, upload.upload_id)
    assert os.path.exists(file_path)
    with open(file_path, "rb") as f:
        assert f.read() == content


def test__add_upload__duplicate_entry__raises_already_existing_exception(
    upload_service, database_session
):
    content = b"test_content"
    content_type = "text/plain"
    upload_service.add_upload(content, content_type)

    with pytest.raises(UploadAlreadyExistingException):
        upload_service.add_upload(content, content_type)


def test__add_upload__file_write_fails__no_dangling_db_record(
    database_session, id_creator, tmp_path
):
    file_storage = OnDiskFileStorage(tmp_path)
    file_storage.add_file = MagicMock(side_effect=OSError("disk full"))
    service = UploadService(file_storage, database_session, id_creator)

    with pytest.raises(OSError):
        service.add_upload(b"test_content", "text/plain")

    result = database_session.exec(select(UploadMetaData)).first()
    assert result is None


def test__add_upload__db_flush_fails__cleans_up_orphan_file(
    database_session, file_storage, id_creator, mocker
):
    service = UploadService(file_storage, database_session, id_creator)
    content = b"test_content"
    mocker.patch.object(database_session, "flush", side_effect=RuntimeError("boom"))

    with pytest.raises(RuntimeError):
        service.add_upload(content, "text/plain")

    upload_id = id_creator.create_upload_id(content)
    file_path = os.path.join(file_storage._base_path, upload_id)
    assert not os.path.exists(file_path)


def test__add_upload__db_flush_fails__cleanup_failure_does_not_mask_original(
    database_session, id_creator, mocker, tmp_path
):
    file_storage = OnDiskFileStorage(tmp_path)
    file_storage.delete_file_content = MagicMock(side_effect=OSError("cleanup failed"))
    service = UploadService(file_storage, database_session, id_creator)
    mocker.patch.object(database_session, "flush", side_effect=RuntimeError("boom"))

    with pytest.raises(RuntimeError):
        service.add_upload(b"test_content", "text/plain")


def test__add_upload__duplicate_entry__cleans_up_orphan_file(
    upload_service, file_storage, id_creator
):
    content = b"test_content"
    upload_service.add_upload(content, "text/plain")

    upload_id = id_creator.create_upload_id(content)
    file_path = os.path.join(file_storage._base_path, upload_id)
    os.remove(file_path)

    with pytest.raises(UploadAlreadyExistingException):
        upload_service.add_upload(content, "text/plain")

    assert not os.path.exists(file_path)


def test__get_upload__valid_id__returns_content_and_type(
    upload_service, database_session, file_storage
):
    content = b"test_content"
    content_type = "text/plain"
    upload = upload_service.add_upload(content, content_type)

    returned = upload_service.get_upload(upload.upload_id)

    assert returned.content == content
    assert returned.content_type == content_type


def test__get_upload__missing_database_entry__raises_not_found_exception(upload_service):
    with pytest.raises(UploadNotFoundException):
        upload_service.get_upload("missing_upload_id")


def test__delete_upload__valid_id__deletes_from_database_and_disk(
    upload_service, database_session, file_storage
):
    content = b"test_content"
    content_type = "text/plain"
    upload = upload_service.add_upload(content, content_type)

    upload_service.delete_upload(upload.upload_id)

    assert (
        database_session.exec(
            select(UploadMetaData).where(UploadMetaData.upload_id == upload.upload_id)
        ).first()
        is None
    )

    file_path = os.path.join(file_storage._base_path, upload.upload_id)
    assert not os.path.exists(file_path)


def test__delete_upload__missing_id__raises_upload_not_found_exception(upload_service):
    with pytest.raises(UploadNotFoundException):
        upload_service.delete_upload("missing_upload_id")
