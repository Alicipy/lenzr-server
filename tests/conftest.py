import os

import pytest
from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel

os.environ["ENVIRONMENT"] = "development"



@pytest.fixture
def database_session():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)
