import pytest

from lenzr_server.models.uploads import UploadMetaData
from lenzr_server.tag_service import TagService, TagUploadNotFoundException


@pytest.fixture
def tag_service(database_session):
    return TagService(database_session)


@pytest.fixture
def upload(database_session):
    model = UploadMetaData(upload_id="test_id", content_type="image/png")
    database_session.add(model)
    database_session.commit()
    database_session.refresh(model)
    return model


def test__set_tags__valid_upload__returns_tag_names(tag_service, upload):
    result = tag_service.set_tags(upload.upload_id, ["landscape", "nature"])

    assert result == ["landscape", "nature"]


def test__set_tags__deduplicates_input(tag_service, upload):
    result = tag_service.set_tags(upload.upload_id, ["landscape", "landscape", "nature"])

    assert result == ["landscape", "nature"]


def test__set_tags__replaces_existing_tags(tag_service, upload):
    tag_service.set_tags(upload.upload_id, ["landscape", "nature"])
    result = tag_service.set_tags(upload.upload_id, ["urban", "night"])

    assert result == ["urban", "night"]


def test__set_tags__empty_list_clears_tags(tag_service, upload):
    tag_service.set_tags(upload.upload_id, ["landscape", "nature"])
    result = tag_service.set_tags(upload.upload_id, [])

    assert result == []


def test__set_tags__nonexistent_upload__raises_not_found(tag_service):
    with pytest.raises(TagUploadNotFoundException):
        tag_service.set_tags("nonexistent", ["landscape"])


def test__get_tags__returns_tag_names(tag_service, upload):
    tag_service.set_tags(upload.upload_id, ["landscape", "nature"])

    result = tag_service.get_tags(upload.upload_id)

    assert sorted(result) == ["landscape", "nature"]


def test__get_tags__no_tags__returns_empty_list(tag_service, upload):
    result = tag_service.get_tags(upload.upload_id)

    assert result == []


def test__get_tags__nonexistent_upload__raises_not_found(tag_service):
    with pytest.raises(TagUploadNotFoundException):
        tag_service.get_tags("nonexistent")


def test__set_tags__reuses_existing_tag_rows(tag_service, database_session):
    upload1 = UploadMetaData(upload_id="upload1", content_type="image/png")
    upload2 = UploadMetaData(upload_id="upload2", content_type="image/png")
    database_session.add(upload1)
    database_session.add(upload2)
    database_session.commit()

    tag_service.set_tags("upload1", ["shared-tag"])
    tag_service.set_tags("upload2", ["shared-tag"])

    from sqlmodel import select

    from lenzr_server.models.tags import Tag

    tags = database_session.exec(select(Tag).where(Tag.name == "shared-tag")).all()
    assert len(tags) == 1


def test__search_by_tags__and_logic__returns_matching_uploads(tag_service, database_session):
    upload1 = UploadMetaData(upload_id="upload1", content_type="image/png")
    upload2 = UploadMetaData(upload_id="upload2", content_type="image/png")
    database_session.add(upload1)
    database_session.add(upload2)
    database_session.commit()

    tag_service.set_tags("upload1", ["landscape", "nature", "sunset"])
    tag_service.set_tags("upload2", ["landscape", "urban"])

    results = tag_service.search_by_tags(["landscape", "nature"])

    assert len(results) == 1
    assert results[0].upload_id == "upload1"
    assert sorted(results[0].tags) == ["landscape", "nature", "sunset"]


def test__search_by_tags__single_tag__returns_all_matching(tag_service, database_session):
    upload1 = UploadMetaData(upload_id="upload1", content_type="image/png")
    upload2 = UploadMetaData(upload_id="upload2", content_type="image/png")
    database_session.add(upload1)
    database_session.add(upload2)
    database_session.commit()

    tag_service.set_tags("upload1", ["landscape"])
    tag_service.set_tags("upload2", ["landscape", "urban"])

    results = tag_service.search_by_tags(["landscape"])

    assert len(results) == 2
    upload_ids = sorted([r.upload_id for r in results])
    assert upload_ids == ["upload1", "upload2"]


def test__search_by_tags__no_matches__returns_empty(tag_service, database_session):
    upload1 = UploadMetaData(upload_id="upload1", content_type="image/png")
    database_session.add(upload1)
    database_session.commit()

    tag_service.set_tags("upload1", ["landscape"])

    results = tag_service.search_by_tags(["nonexistent"])

    assert results == []


def test__search_by_tags__empty_input__returns_empty(tag_service):
    results = tag_service.search_by_tags([])

    assert results == []


def test__list_all_tags__returns_sorted_tag_names(tag_service, database_session):
    upload1 = UploadMetaData(upload_id="upload1", content_type="image/png")
    upload2 = UploadMetaData(upload_id="upload2", content_type="image/png")
    database_session.add(upload1)
    database_session.add(upload2)
    database_session.commit()

    tag_service.set_tags("upload1", ["nature", "landscape"])
    tag_service.set_tags("upload2", ["urban"])

    result = tag_service.list_all_tags()

    assert result == ["landscape", "nature", "urban"]


def test__list_all_tags__no_tags__returns_empty(tag_service):
    result = tag_service.list_all_tags()

    assert result == []


def test__set_tags__idempotent__same_tags_twice(tag_service, upload):
    tag_service.set_tags(upload.upload_id, ["landscape", "nature"])
    result = tag_service.set_tags(upload.upload_id, ["landscape", "nature"])

    assert result == ["landscape", "nature"]
    assert sorted(tag_service.get_tags(upload.upload_id)) == ["landscape", "nature"]


def test__get_tags__after_clear__returns_empty(tag_service, upload):
    tag_service.set_tags(upload.upload_id, ["landscape", "nature"])
    tag_service.set_tags(upload.upload_id, [])

    result = tag_service.get_tags(upload.upload_id)

    assert result == []


def test__search_by_tags__duplicate_input__deduplicates(tag_service, database_session):
    upload1 = UploadMetaData(upload_id="upload1", content_type="image/png")
    database_session.add(upload1)
    database_session.commit()

    tag_service.set_tags("upload1", ["landscape"])

    results = tag_service.search_by_tags(["landscape", "landscape"])

    assert len(results) == 1
    assert results[0].upload_id == "upload1"


def test__list_all_tags__orphaned_tags_persist(tag_service, upload):
    tag_service.set_tags(upload.upload_id, ["landscape", "nature"])
    tag_service.set_tags(upload.upload_id, [])

    result = tag_service.list_all_tags()

    assert result == ["landscape", "nature"]


def test__list_all_tags__shared_tags_not_duplicated(tag_service, database_session):
    upload1 = UploadMetaData(upload_id="upload1", content_type="image/png")
    upload2 = UploadMetaData(upload_id="upload2", content_type="image/png")
    database_session.add(upload1)
    database_session.add(upload2)
    database_session.commit()

    tag_service.set_tags("upload1", ["landscape", "nature"])
    tag_service.set_tags("upload2", ["landscape", "urban"])

    result = tag_service.list_all_tags()

    assert result == ["landscape", "nature", "urban"]
