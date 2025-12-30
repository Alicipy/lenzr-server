import pytest
import sqlalchemy.exc

from lenzr_server.models.uploads import UploadMetaData


def test__upload_metadata_model__inserted_correct_data(database_session):
    model = UploadMetaData(upload_id="test_id", content_type="image/png")

    database_session.add(model)
    database_session.commit()
    database_session.refresh(model)

    assert model.upload_id == "test_id"
    assert model.content_type == "image/png"
    assert model.pk is not None
    assert model.created_at is not None


def test__upload_metadata_model__inserted_multiple_rows(database_session):
    model1 = UploadMetaData(upload_id="test_id1", content_type="image/png")

    model2 = UploadMetaData(upload_id="test_id2", content_type="image/jpg")

    database_session.add(model1)
    database_session.add(model2)
    database_session.commit()


def test__upload_metadata_model_no_upload_id_raises_error(database_session):
    model = UploadMetaData(content_type="image/png")

    database_session.add(model)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        database_session.commit()


def test__upload_metadata_model_no_content_type_raises_error(database_session):
    model = UploadMetaData(upload_id="test_id")

    database_session.add(model)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        database_session.commit()


def test_upload_metadata_model_duplicates_raise_errors(database_session):
    model1 = UploadMetaData(upload_id="test_id", content_type="image/png")

    model2 = UploadMetaData(upload_id="test_id", content_type="image/png")

    database_session.add(model1)
    database_session.commit()

    database_session.add(model2)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        database_session.commit()
