from typing import Protocol

from lenzr_server.types import UploadID


class IDCreator(Protocol):
    def create_upload_id(self, content: bytes) -> UploadID:
        pass
