from fastapi import Depends
from sqlmodel import Session

from lenzr_server.db import engine
from lenzr_server.file_storages.on_disk_file_storage import OnDiskFileStorage
from lenzr_server.upload_id_creators.hashing_id_creator import HashingIDCreator
from lenzr_server.upload_id_creators.id_creator import IDCreator
from lenzr_server.upload_service import UploadService


def get_id_creator():
    creator = HashingIDCreator(seed=32)
    return creator


def get_file_storage():
    file_storage = OnDiskFileStorage(base_path="/tmp/lenzr_server")
    return file_storage


def get_db_session():
    with Session(engine) as session:
        yield session


def get_upload_service(
    file_storage: OnDiskFileStorage = Depends(get_file_storage),
    db_session: Session = Depends(get_db_session),
    upload_id_creator: IDCreator = Depends(get_id_creator),
):
    upload_service = UploadService(
        file_storage=file_storage,
        database_session=db_session,
        upload_id_creator=upload_id_creator,
    )
    return upload_service
