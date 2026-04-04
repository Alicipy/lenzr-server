from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from lenzr_server.models.uploads import UploadMetaDataBase
from lenzr_server.types import TagName, UploadID

if TYPE_CHECKING:
    from lenzr_server.tag_service import UploadWithTags


class UploadMetaDataCreateResponse(UploadMetaDataBase):
    tags: list[TagName] = []


class UploadMetaDataPublicResponse(UploadMetaDataBase):
    pass


class UploadMetaDataDeleteResponse(UploadMetaDataBase):
    pass


class ErrorResponse(BaseModel):
    detail: str

    model_config = ConfigDict(json_schema_extra={"example": {"detail": "Upload not found"}})


class TagsUpdateRequest(BaseModel):
    tags: list[TagName]


class UploadWithTagsResponse(BaseModel):
    upload_id: UploadID
    tags: list[TagName]
    created_at: datetime.datetime
    content_type: str

    @classmethod
    def from_upload_with_tags(cls, uwt: UploadWithTags) -> UploadWithTagsResponse:
        return cls(
            upload_id=uwt.upload_id,
            tags=uwt.tags,
            created_at=uwt.created_at,
            content_type=uwt.content_type,
        )


class TagListResponse(BaseModel):
    tags: list[TagName]
