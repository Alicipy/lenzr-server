import datetime
import uuid

from sqlmodel import Field, SQLModel


class LenzrServerModel(SQLModel):
    pass


class UploadMetaData(LenzrServerModel, table=True):
    pk: uuid.UUID | None = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    upload_id: str = Field(max_length=32, index=True, unique=True)
    content_type: str = Field(max_length=32)
