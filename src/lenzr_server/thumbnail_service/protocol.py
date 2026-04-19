from dataclasses import dataclass
from typing import Protocol

from lenzr_server.types import UploadID


@dataclass(frozen=True)
class Thumbnail:
    content: bytes
    content_type: str


class InvalidImageException(Exception):
    def __init__(self, detail: str = "Image cannot be decoded"):
        self.detail = detail
        super().__init__(detail)


class ThumbnailService(Protocol):
    def get_thumbnail(self, upload_id: UploadID, content: bytes) -> Thumbnail:
        """Return the thumbnail for ``upload_id``, generating from ``content`` on cache miss.

        Raises ``InvalidImageException`` if ``content`` cannot be decoded as an image.
        """
        ...

    def evict(self, upload_id: UploadID) -> None:
        """Drop any cached thumbnail for ``upload_id``. No-op if absent."""
        ...
