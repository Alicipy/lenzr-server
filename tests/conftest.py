import io
import os
import tempfile
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, event
from sqlmodel import Session, SQLModel

from lenzr_server.main import app
from lenzr_server.thumbnail_service import InMemoryThumbnailCache, InMemoryThumbnailService

os.environ["ENVIRONMENT"] = "development"
os.environ["UPLOAD_STORAGE_PATH"] = tempfile.mkdtemp()


@pytest.fixture
def database_session():
    engine = create_engine("sqlite:///:memory:")
    event.listen(engine, "connect", lambda conn, _: conn.execute("PRAGMA foreign_keys=ON"))
    SQLModel.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session
        if session.is_active:
            session.commit()
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def set_env_variables(mocker):
    mocker.patch.dict(os.environ, {"LENZR_USERNAME": "test_user", "LENZR_PASSWORD": "test_pass"})


@pytest.fixture
def client(thumbnail_cache):
    with TestClient(app) as c:
        app.state.thumbnail_cache = thumbnail_cache
        yield c


@pytest.fixture
def create_test_image() -> Callable[..., bytes]:
    def _create(
        width: int = 800,
        height: int = 600,
        image_format: str = "PNG",
        mode: str = "RGB",
        color: str | tuple = "red",
    ) -> bytes:
        image = Image.new(mode, (width, height), color=color)
        output = io.BytesIO()
        image.save(output, format=image_format)
        return output.getvalue()

    return _create


@pytest.fixture
def thumbnail_cache() -> InMemoryThumbnailCache:
    return InMemoryThumbnailCache()


@pytest.fixture
def thumbnail_service(thumbnail_cache: InMemoryThumbnailCache) -> InMemoryThumbnailService:
    return InMemoryThumbnailService(cache=thumbnail_cache)
