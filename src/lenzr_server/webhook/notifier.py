from datetime import datetime
from typing import Literal, Protocol

from pydantic import BaseModel

from lenzr_server.types import UploadID


class WebhookPayload(BaseModel):
    event: Literal["upload.created"]
    upload_id: UploadID
    delivery_id: str
    timestamp: datetime


class WebhookNotifier(Protocol):
    def send(self, upload_id: UploadID, creation_time: datetime) -> None: ...


class NoOpWebhookNotifier:
    def send(self, upload_id: UploadID, creation_time: datetime) -> None:
        return None
