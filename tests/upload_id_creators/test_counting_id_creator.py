import pytest

from lenzr_server.upload_id_creators.counting_id_creator import CountingIdCreator


@pytest.fixture
def id_creator():
    return CountingIdCreator()


def test__create_upload_id__returns_string(id_creator):
    upload_id = id_creator.create_upload_id(b"test_content")
    assert isinstance(upload_id, str)


def test_create_upload_id_increments_id(id_creator):
    """Test that create_upload_id generates incrementing IDs."""
    id_1 = id_creator.create_upload_id(b"test_content_1")
    id_2 = id_creator.create_upload_id(b"test_content_2")
    assert id_1 != id_2
    assert id_1 == "1"
    assert id_2 == "2"
