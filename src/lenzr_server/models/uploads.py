import datetime
import uuid

from sqlmodel import Field, SQLModel


class LenzrServerModel(SQLModel):
    pass


class UploadMetaDataBase(LenzrServerModel):
    upload_id: str = Field(max_length=32, index=True, unique=True)


class UploadMetaData(UploadMetaDataBase, table=True):
    pk: uuid.UUID | None = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    content_type: str = Field(max_length=32)


class UploadMetaDataCreateResponse(UploadMetaDataBase):
    pass


class UploadMetaDataPublicResponse(UploadMetaDataBase):
    pass


class UploadMetaDataDeleteResponse(UploadMetaDataBase):
    pass
