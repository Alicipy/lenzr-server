import datetime
from dataclasses import dataclass

import sqlalchemy as sa
import sqlalchemy.exc
from sqlmodel import Session, col, select

from lenzr_server.exceptions import NotFoundException
from lenzr_server.models.tags import Tag, UploadTag
from lenzr_server.models.uploads import UploadMetaData
from lenzr_server.types import TagName, UploadID


class TagUploadNotFoundException(NotFoundException):
    def __init__(self):
        super().__init__(detail="Upload not found")


@dataclass
class UploadWithTags:
    upload_id: UploadID
    tags: list[TagName]
    created_at: datetime.datetime
    content_type: str


class TagService:
    def __init__(self, database_session: Session):
        self._database_session = database_session

    def _get_upload(self, upload_id: UploadID) -> UploadMetaData:
        query = select(UploadMetaData).where(col(UploadMetaData.upload_id) == upload_id)
        try:
            return self._database_session.exec(query).one()
        except sqlalchemy.exc.NoResultFound:
            raise TagUploadNotFoundException()

    def _get_tags_by_upload_pk(self, upload_pk) -> list[TagName]:
        query = (
            select(Tag.name)
            .join(UploadTag, col(UploadTag.tag_pk) == Tag.pk)
            .where(col(UploadTag.upload_pk) == upload_pk)
        )
        return list(self._database_session.exec(query).all())

    def _get_or_create_tags(self, names: list[str]) -> dict[str, Tag]:
        if not names:
            return {}
        existing = self._database_session.exec(select(Tag).where(col(Tag.name).in_(names))).all()
        tag_map = {tag.name: tag for tag in existing}
        for name in names:
            if name not in tag_map:
                tag = Tag(name=name)
                self._database_session.add(tag)
                tag_map[name] = tag
        self._database_session.flush()
        return tag_map

    def set_tags(self, upload_id: UploadID, tag_names: list[TagName]) -> list[TagName]:
        upload = self._get_upload(upload_id)
        upload_pk = upload.pk

        self._database_session.exec(
            sa.delete(UploadTag).where(col(UploadTag.upload_pk) == upload_pk)
        )

        unique_names = list(dict.fromkeys(tag_names))
        tag_map = self._get_or_create_tags(unique_names)
        for name in unique_names:
            self._database_session.add(UploadTag(upload_pk=upload_pk, tag_pk=tag_map[name].pk))

        self._database_session.flush()
        return unique_names

    def get_upload_with_tags(self, upload_id: UploadID) -> UploadWithTags:
        upload = self._get_upload(upload_id)
        tags = self._get_tags_by_upload_pk(upload.pk)
        return UploadWithTags(
            upload_id=upload.upload_id,
            tags=tags,
            created_at=upload.created_at,
            content_type=upload.content_type,
        )

    def get_tags(self, upload_id: UploadID) -> list[TagName]:
        upload = self._get_upload(upload_id)
        return self._get_tags_by_upload_pk(upload.pk)

    def _to_uploads_with_tags(self, uploads: list[UploadMetaData]) -> list[UploadWithTags]:
        if not uploads:
            return []

        upload_pks = [u.pk for u in uploads]
        tag_rows = self._database_session.exec(
            select(UploadTag.upload_pk, Tag.name)
            .join(Tag, col(Tag.pk) == UploadTag.tag_pk)
            .where(col(UploadTag.upload_pk).in_(upload_pks))
        ).all()
        tags_by_pk: dict = {}
        for upload_pk, tag_name in tag_rows:
            tags_by_pk.setdefault(upload_pk, []).append(tag_name)

        return [
            UploadWithTags(
                upload_id=upload.upload_id,
                tags=tags_by_pk.get(upload.pk, []),
                created_at=upload.created_at,
                content_type=upload.content_type,
            )
            for upload in uploads
        ]

    def list_with_tags(
        self,
        tag_names: list[TagName] | None = None,
        offset: int = 0,
        limit: int = 10,
    ) -> list[UploadWithTags]:
        query = select(UploadMetaData)

        if tag_names:
            unique_names = list(dict.fromkeys(tag_names))
            # AND logic: only uploads that have ALL requested tags
            query = (
                query.join(UploadTag, col(UploadTag.upload_pk) == UploadMetaData.pk)
                .join(Tag, col(Tag.pk) == UploadTag.tag_pk)
                .where(col(Tag.name).in_(unique_names))
                .group_by(col(UploadMetaData.pk))
                .having(sa.func.count(sa.distinct(col(Tag.name))) == len(unique_names))
            )

        query = query.order_by(col(UploadMetaData.created_at).desc()).offset(offset).limit(limit)
        uploads = list(self._database_session.exec(query).all())
        return self._to_uploads_with_tags(uploads)

    def list_all_tags(self, offset: int = 0, limit: int = 100) -> list[TagName]:
        query = select(Tag.name).order_by(Tag.name).offset(offset).limit(limit)
        return list(self._database_session.exec(query).all())
