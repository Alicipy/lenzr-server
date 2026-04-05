import uuid

import pytest
import sqlalchemy.exc
from sqlmodel import select

from lenzr_server.models.tags import Tag, UploadTag
from lenzr_server.models.uploads import UploadMetaData


def _bulk_refresh(session, *models):
    for model in models:
        session.refresh(model)


@pytest.fixture
def upload(database_session):
    model = UploadMetaData(upload_id="test_id", content_type="image/png")
    database_session.add(model)
    database_session.commit()
    database_session.refresh(model)
    return model


@pytest.fixture
def tag(database_session):
    t = Tag(name="landscape")
    database_session.add(t)
    database_session.commit()
    database_session.refresh(t)
    return t


def test__tag_model__inserted_correct_data(tag):
    assert tag.name == "landscape"
    assert tag.pk is not None


def test__tag_model__duplicate_name_raises_error(database_session, tag):
    database_session.add(Tag(name="landscape"))
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        database_session.commit()


def test__tag_model__no_name_raises_error(database_session):
    database_session.add(Tag())
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        database_session.commit()


def test__upload_tag_model__inserted_correct_data(database_session, upload, tag):
    upload_tag = UploadTag(upload_pk=upload.pk, tag_pk=tag.pk)
    database_session.add(upload_tag)
    database_session.commit()


def test__upload_tag_model__duplicate_raises_error(database_session, upload, tag):
    upload_tag1 = UploadTag(upload_pk=upload.pk, tag_pk=tag.pk)
    database_session.add(upload_tag1)
    database_session.commit()
    database_session.expunge(upload_tag1)

    upload_tag2 = UploadTag(upload_pk=upload.pk, tag_pk=tag.pk)
    database_session.add(upload_tag2)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        database_session.commit()


def test__upload_tag_model__invalid_upload_fk_raises_error(database_session, tag):
    database_session.add(UploadTag(upload_pk=uuid.uuid4(), tag_pk=tag.pk))
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        database_session.commit()


def test__upload_tag_model__invalid_tag_fk_raises_error(database_session, upload):
    database_session.add(UploadTag(upload_pk=upload.pk, tag_pk=uuid.uuid4()))
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        database_session.commit()


def test__upload_tag_model__cascade_delete_upload(database_session, upload, tag):
    database_session.add(UploadTag(upload_pk=upload.pk, tag_pk=tag.pk))
    database_session.commit()

    database_session.delete(upload)
    database_session.commit()

    assert database_session.exec(select(UploadTag)).all() == []
    assert len(database_session.exec(select(Tag)).all()) == 1


def test__upload_tag_model__multiple_tags_per_upload(database_session, upload):
    tag1 = Tag(name="landscape")
    tag2 = Tag(name="nature")
    database_session.add(tag1)
    database_session.add(tag2)
    database_session.commit()
    _bulk_refresh(database_session, tag1, tag2)

    database_session.add(UploadTag(upload_pk=upload.pk, tag_pk=tag1.pk))
    database_session.add(UploadTag(upload_pk=upload.pk, tag_pk=tag2.pk))
    database_session.commit()

    assert len(database_session.exec(select(UploadTag)).all()) == 2


def test__upload_tag_model__restrict_delete_tag_with_references(database_session, upload, tag):
    database_session.add(UploadTag(upload_pk=upload.pk, tag_pk=tag.pk))
    database_session.commit()

    database_session.delete(tag)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        database_session.commit()


def test__upload_tag_model__multiple_uploads_share_one_tag(database_session, tag):
    upload1 = UploadMetaData(upload_id="test_id1", content_type="image/png")
    upload2 = UploadMetaData(upload_id="test_id2", content_type="image/png")
    database_session.add(upload1)
    database_session.add(upload2)
    database_session.commit()
    _bulk_refresh(database_session, upload1, upload2)

    database_session.add(UploadTag(upload_pk=upload1.pk, tag_pk=tag.pk))
    database_session.add(UploadTag(upload_pk=upload2.pk, tag_pk=tag.pk))
    database_session.commit()

    assert len(database_session.exec(select(UploadTag)).all()) == 2


def test__upload_tag_model__cascade_delete_upload_with_multiple_tags(database_session, upload):
    tag1 = Tag(name="landscape")
    tag2 = Tag(name="nature")
    tag3 = Tag(name="sunset")
    database_session.add_all([tag1, tag2, tag3])
    database_session.commit()
    _bulk_refresh(database_session, tag1, tag2, tag3)

    database_session.add(UploadTag(upload_pk=upload.pk, tag_pk=tag1.pk))
    database_session.add(UploadTag(upload_pk=upload.pk, tag_pk=tag2.pk))
    database_session.add(UploadTag(upload_pk=upload.pk, tag_pk=tag3.pk))
    database_session.commit()

    database_session.delete(upload)
    database_session.commit()

    assert database_session.exec(select(UploadTag)).all() == []
    assert len(database_session.exec(select(Tag)).all()) == 3
