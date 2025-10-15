import pytest
import sqlalchemy.exc
from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel

from lenzr_server.models import UploadMetaData


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

    SQLModel.metadata.drop_all(engine)

def test__upload_metadata_model__inserted_correct_data(session):
    model = UploadMetaData(
        upload_id="test_id",
        content_type="image/png"
    )

    session.add(model)
    session.commit()
    session.refresh(model)

    assert model.upload_id == "test_id"
    assert model.content_type == "image/png"
    assert model.pk is not None
    assert model.created_at is not None

def test__upload_metadata_model__inserted_multiple_rows(session):
    model1 = UploadMetaData(
        upload_id="test_id1",
        content_type="image/png"
    )

    model2 = UploadMetaData(
        upload_id="test_id2",
        content_type="image/jpg"
    )

    session.add(model1)
    session.add(model2)
    session.commit()

def test__upload_metadata_model_no_upload_id_raises_error(session):
    model = UploadMetaData(
        content_type="image/png"
    )

    session.add(model)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        session.commit()

def test__upload_metadata_model_no_content_type_raises_error(session):
    model = UploadMetaData(
        upload_id="test_id"
    )

    session.add(model)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        session.commit()

def test_upload_metadata_model_duplicates_raise_errors(session):
    model1 = UploadMetaData(
        upload_id="test_id",
        content_type="image/png"
    )

    model2 = UploadMetaData(
        upload_id="test_id",
        content_type="image/png"
    )

    session.add(model1)
    session.commit()

    session.add(model2)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        session.commit()
