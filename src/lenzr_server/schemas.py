from pydantic import BaseModel, ConfigDict

from lenzr_server.models.uploads import UploadMetaDataBase
from lenzr_server.types import TagName, UploadID


class UploadMetaDataCreateResponse(UploadMetaDataBase):
    pass


class UploadMetaDataPublicResponse(UploadMetaDataBase):
    pass


class UploadMetaDataDeleteResponse(UploadMetaDataBase):
    pass


class ErrorResponse(BaseModel):
    detail: str

    model_config = ConfigDict(json_schema_extra={"example": {"detail": "Upload not found"}})


class TagsUpdateRequest(BaseModel):
    tags: list[TagName]


class UploadTagsResponse(BaseModel):
    upload_id: UploadID
    tags: list[TagName]


class TagListResponse(BaseModel):
    tags: list[TagName]
