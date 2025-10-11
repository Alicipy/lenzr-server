from typing import Protocol


class IDCreator(Protocol):

    def create_upload_id(self, content: bytes) -> str:
        pass