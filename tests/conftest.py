import os
import tempfile

import pytest
from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel

os.environ["ENVIRONMENT"] = "development"
os.environ["UPLOAD_STORAGE_PATH"] = tempfile.mkdtemp()


@pytest.fixture
def database_session():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def set_env_variables(mocker):
    mocker.patch.dict(os.environ, {"LENZR_USERNAME": "test_user", "LENZR_PASSWORD": "test_pass"})
