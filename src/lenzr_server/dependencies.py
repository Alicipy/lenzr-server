import os

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlmodel import Session

import lenzr_server.security as security
from lenzr_server.db import engine
from lenzr_server.file_storages.file_storage import FileStorage
from lenzr_server.file_storages.on_disk_file_storage import OnDiskFileStorage
from lenzr_server.tag_service import TagService
from lenzr_server.thumbnail_service import InMemoryThumbnailService, ThumbnailService
from lenzr_server.upload_id_creators.hashing_id_creator import HashingIDCreator
from lenzr_server.upload_id_creators.id_creator import IDCreator
from lenzr_server.upload_service import UploadService
from lenzr_server.webhook import WebhookNotifier

DEFAULT_MAX_UPLOAD_BYTES = 25 * 1024 * 1024

_id_creator = HashingIDCreator(seed=32)


def get_id_creator() -> IDCreator:
    return _id_creator


def get_max_upload_bytes() -> int:
    return int(os.environ.get("MAX_UPLOAD_BYTES", DEFAULT_MAX_UPLOAD_BYTES))


def get_file_storage():
    storage_path = os.environ["UPLOAD_STORAGE_PATH"]
    file_storage = OnDiskFileStorage(base_path=storage_path)
    return file_storage


def get_db_session():
    with Session(engine, expire_on_commit=False) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def get_upload_service(
    file_storage: FileStorage = Depends(get_file_storage),
    db_session: Session = Depends(get_db_session),
    upload_id_creator: IDCreator = Depends(get_id_creator),
) -> UploadService:
    return UploadService(
        file_storage=file_storage,
        database_session=db_session,
        upload_id_creator=upload_id_creator,
    )


def get_tag_service(
    db_session: Session = Depends(get_db_session),
):
    return TagService(database_session=db_session)


def get_thumbnail_service(request: Request) -> ThumbnailService:
    return InMemoryThumbnailService(cache=request.app.state.thumbnail_cache)


def get_webhook_notifier(request: Request) -> WebhookNotifier:
    return request.app.state.webhook_notifier


http_basic_auth = HTTPBasic()


def check_login_valid(credentials: HTTPBasicCredentials = Depends(http_basic_auth)):
    is_logged_in = security.is_logged_in(credentials.username, credentials.password)
    if not is_logged_in:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return None
