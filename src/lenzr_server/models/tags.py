import uuid

import sqlalchemy as sa
from sqlmodel import Field

from lenzr_server.models.uploads import LenzrServerModel


class Tag(LenzrServerModel, table=True):
    pk: uuid.UUID | None = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=64, unique=True, index=True)


class UploadTag(LenzrServerModel, table=True):
    upload_pk: uuid.UUID = Field(
        sa_column=sa.Column(
            sa.Uuid,
            sa.ForeignKey("uploadmetadata.pk", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    tag_pk: uuid.UUID = Field(
        sa_column=sa.Column(
            sa.Uuid,
            sa.ForeignKey("tag.pk", ondelete="RESTRICT"),
            primary_key=True,
        ),
    )
