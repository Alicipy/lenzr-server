from pydantic import BaseModel, ConfigDict

from lenzr_server.models.uploads import UploadMetaDataBase


class UploadMetaDataCreateResponse(UploadMetaDataBase):
    pass


class UploadMetaDataPublicResponse(UploadMetaDataBase):
    pass


class UploadMetaDataDeleteResponse(UploadMetaDataBase):
    pass


class ErrorResponse(BaseModel):
    detail: str

    model_config = ConfigDict(json_schema_extra={"example": {"detail": "Upload not found"}})
