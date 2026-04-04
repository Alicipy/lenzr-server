import logging

import sqlalchemy.exc
from sqlmodel import Session, desc, select

from lenzr_server.exceptions import AlreadyExistingException, NotFoundException
from lenzr_server.file_storages.file_storage import FileID, FileStorage
from lenzr_server.models.uploads import UploadMetaData
from lenzr_server.types import UploadID
from lenzr_server.upload_id_creators.id_creator import IDCreator


class UploadAlreadyExistingException(AlreadyExistingException):
    def __init__(self, upload_id: UploadID):
        self.upload_id = upload_id
        super().__init__(detail="Upload already exists")


class UploadNotFoundException(NotFoundException):
    def __init__(self):
        super().__init__(detail="Upload not found")


class UploadService:
    def __init__(
        self,
        file_storage: FileStorage,
        database_session: Session,
        upload_id_creator: IDCreator,
    ):
        self._database_session = database_session
        self._file_storage = file_storage
        self._upload_id_creator = upload_id_creator

    def add_upload(self, content: bytes, content_type: str) -> UploadMetaData:
        upload_id = self._upload_id_creator.create_upload_id(content)
        file_id = FileID(upload_id)

        self._file_storage.add_file(file_id, content)

        try:
            upload_metadata = UploadMetaData(
                upload_id=upload_id,
                content_type=content_type,
            )
            self._database_session.add(upload_metadata)
            self._database_session.flush()
            self._database_session.refresh(upload_metadata)
        except sqlalchemy.exc.IntegrityError:
            self._database_session.rollback()
            logging.error(f"Upload {upload_id} already stored")
            self._file_storage.delete_file_content(file_id)
            raise UploadAlreadyExistingException(upload_id=upload_id)

        return upload_metadata

    def get_id_for_content(self, content: bytes) -> UploadID:
        upload_id = self._upload_id_creator.create_upload_id(content)
        return upload_id

    def get_upload(self, upload_id: UploadID) -> tuple[bytes, str]:
        query = select(UploadMetaData).where(UploadMetaData.upload_id == upload_id)
        try:
            metadata_entry = self._database_session.exec(query).one()
            content_type = metadata_entry.content_type
        except sqlalchemy.exc.NoResultFound:
            logging.error(f"Upload {upload_id} not found in database")
            raise UploadNotFoundException()

        try:
            file_id = FileID(upload_id)
            content = self._file_storage.get_file_content(file_id)
        except FileNotFoundError:
            logging.error(f"Upload {upload_id} not found on disk")
            raise UploadNotFoundException()

        return content, content_type

    def delete_upload(self, upload_id: UploadID) -> UploadMetaData:
        query = select(UploadMetaData).where(UploadMetaData.upload_id == upload_id)
        try:
            upload = self._database_session.exec(query).one()
            self._database_session.delete(upload)
            self._database_session.flush()
        except sqlalchemy.exc.NoResultFound:
            logging.error(f"Upload {upload_id} not found in database")
            raise UploadNotFoundException()

        try:
            file_id = FileID(upload_id)
            self._file_storage.delete_file_content(file_id)
        except FileNotFoundError:
            logging.error(f"Upload {upload_id} not found on disk")
            raise UploadNotFoundException()

        return upload

    def list_uploads(self, offset: int = 0, limit: int = 10) -> list[UploadMetaData]:
        query = (
            select(UploadMetaData)
            .order_by(desc(UploadMetaData.created_at))
            .offset(offset)
            .limit(limit)
        )

        ids = self._database_session.exec(query).all()

        return ids
