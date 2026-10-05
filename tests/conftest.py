# ruff: noqa: E402
# Set env before importing lenzr_server: db.py builds its engine from DATABASE_URL.
import datetime
import io
import os
import tempfile
from collections.abc import Callable

os.environ["ENVIRONMENT"] = "development"
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp(prefix='lenzr-test-')}/db.sqlite3"
os.environ["UPLOAD_STORAGE_PATH"] = tempfile.mkdtemp()

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, event
from sqlmodel import Session, SQLModel, col, select

from lenzr_server.main import app
from lenzr_server.models.tags import Tag, UploadTag
from lenzr_server.models.uploads import UploadMetaData
from lenzr_server.thumbnail_service import InMemoryThumbnailCache, InMemoryThumbnailService

UPLOAD_BASE_TIME = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)


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
    engine.dispose()


@pytest.fixture
def add_upload(database_session) -> Callable[..., UploadMetaData]:
    """Add a tagged upload created `hour` hours after UPLOAD_BASE_TIME."""

    def _add(upload_id: str, tags: list[str], hour: int = 0) -> UploadMetaData:
        created_at = UPLOAD_BASE_TIME + datetime.timedelta(hours=hour)
        upload = UploadMetaData(
            upload_id=upload_id, content_type="image/png", created_at=created_at
        )
        database_session.add(upload)
        database_session.flush()
        for name in tags:
            tag = database_session.exec(select(Tag).where(col(Tag.name) == name)).first()
            if tag is None:
                tag = Tag(name=name)
                database_session.add(tag)
                database_session.flush()
            database_session.add(UploadTag(upload_pk=upload.pk, tag_pk=tag.pk))
        database_session.flush()
        return upload

    return _add


@pytest.fixture(autouse=True)
def set_env_variables(mocker):
    mocker.patch.dict(
        os.environ,
        {"LENZR_USERNAME": "test_user", "LENZR_PASSWORD": "test_pass"},
    )
    mocker.patch.dict(
        os.environ,
        {
            "WEBHOOK_URL": "",
            "WEBHOOK_SECRET": "",
            "EMBEDDING_PROVIDER": "",
            "EMBEDDING_LOCAL_MODEL": "",
            "SEMANTIC_SIMILARITY_THRESHOLD": "",
        },
        clear=False,
    )


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
