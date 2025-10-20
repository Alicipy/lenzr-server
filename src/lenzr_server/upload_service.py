import logging

import sqlalchemy.exc
from sqlmodel import Session, select

from lenzr_server.file_storages.on_disk_file_storage import (
    OnDiskFileStorage,
    OnDiskSearchParameters,
)
from lenzr_server.models import UploadMetaData
from lenzr_server.types import UploadID
from lenzr_server.upload_id_creators.id_creator import IDCreator


class UploadServiceException(Exception):
    pass


class AlreadyExistingException(UploadServiceException):
    pass


class NotFoundException(UploadServiceException):
    pass


class UploadService:
    def __init__(
        self,
        file_storage: OnDiskFileStorage,
        database_session: Session,
        upload_id_creator: IDCreator,
    ):
        self._database_session = database_session
        self._file_storage = file_storage
        self._upload_id_creator = upload_id_creator

    def add_upload(self, content: bytes, content_type: str) -> UploadID:
        upload_id = self._upload_id_creator.create_upload_id(content)

        try:
            upload_metadata = UploadMetaData(
                upload_id=upload_id,
                content_type=content_type,
            )
            self._database_session.add(upload_metadata)
            self._database_session.commit()

            file_metadata = OnDiskSearchParameters(on_disk_filename=upload_id)
            self._file_storage.add_file(file_metadata, content)

            self._database_session.refresh(upload_metadata)

        except sqlalchemy.exc.IntegrityError:
            logging.error(f"Upload {upload_id} already stored")
            raise AlreadyExistingException

        return upload_id

    def get_upload(self, upload_id: UploadID) -> tuple[bytes, str]:
        query = select(UploadMetaData).where(UploadMetaData.upload_id == upload_id)
        try:
            metadata_entry = self._database_session.exec(query).one()
            content_type = metadata_entry.content_type
        except sqlalchemy.exc.NoResultFound:
            logging.error(f"Upload {upload_id} not found in database")
            raise NotFoundException

        try:
            file_meta_data = OnDiskSearchParameters(on_disk_filename=upload_id)
            content = self._file_storage.get_file_content(file_meta_data)
        except FileNotFoundError:
            logging.error(f"Upload {upload_id} not found on disk")
            raise NotFoundException

        return content, content_type

    def list_uploads(self) -> list[UploadID]:
        query = select(UploadMetaData.upload_id)
        ids = self._database_session.exec(query).all()

        return ids
