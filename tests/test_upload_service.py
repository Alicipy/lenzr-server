import os

import pytest
from sqlmodel import select

from lenzr_server.file_storages.on_disk_file_storage import OnDiskFileStorage
from lenzr_server.models import UploadMetaData
from lenzr_server.upload_id_creators.hashing_id_creator import HashingIDCreator
from lenzr_server.upload_service import AlreadyExistingException, NotFoundException, UploadService


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

    upload_id = upload_service.add_upload(content, content_type)

    # Verify database entry
    result = database_session.exec(
        select(UploadMetaData).where(UploadMetaData.upload_id == upload_id)
    ).first()
    assert result is not None
    assert result.upload_id == upload_id
    assert result.content_type == content_type

    # Verify file storage
    file_path = os.path.join(file_storage._base_path, upload_id)
    assert os.path.exists(file_path)
    with open(file_path, "rb") as f:
        assert f.read() == content


def test__add_upload__duplicate_entry__raises_already_existing_exception(
    upload_service, database_session
):
    content = b"test_content"
    content_type = "text/plain"
    upload_service.add_upload(content, content_type)

    with pytest.raises(AlreadyExistingException):
        upload_service.add_upload(content, content_type)


def test__get_upload__valid_id__returns_content_and_type(
    upload_service, database_session, file_storage
):
    content = b"test_content"
    content_type = "text/plain"
    upload_id = upload_service.add_upload(content, content_type)

    returned_content, returned_content_type = upload_service.get_upload(upload_id)

    assert returned_content == content
    assert returned_content_type == content_type


def test__get_upload__missing_database_entry__raises_not_found_exception(upload_service):
    with pytest.raises(NotFoundException):
        upload_service.get_upload("missing_upload_id")


def test__list_uploads__valid_request__returns_list_of_ids(upload_service, database_session):
    upload_ids = [
        upload_service.add_upload(b"content_1", "text/plain"),
        upload_service.add_upload(b"content_2", "text/html"),
    ]

    returned_ids = upload_service.list_uploads()
    assert sorted(upload_ids) == sorted(returned_ids)


def test__list_uploads__upload_two_files__returns_ordered_ids(upload_service, database_session):
    first_upload_id = upload_service.add_upload(b"content_1", "text/plain")
    second_upload_id = upload_service.add_upload(b"content_2", "text/html")

    returned_ids = upload_service.list_uploads()

    assert returned_ids == [second_upload_id, first_upload_id]


def test__list_uploads__with_limit_and_offset__returns_paginated_list_of_ids(
    upload_service, database_session
):
    upload_ids = [
        upload_service.add_upload(f"content_{i}".encode(), "text/plain") for i in range(5)
    ]

    returned_ids = upload_service.list_uploads(offset=1, limit=2)

    assert returned_ids[0] == upload_ids[3]
    assert returned_ids[1] == upload_ids[2]
