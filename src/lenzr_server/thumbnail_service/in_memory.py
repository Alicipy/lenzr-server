import io
import threading
from collections import OrderedDict

from PIL import Image, UnidentifiedImageError

from lenzr_server.thumbnail_service.protocol import InvalidImageException, Thumbnail
from lenzr_server.types import UploadID

MAX_CACHE_SIZE = 1000
MAX_DIMENSION = 200
THUMBNAIL_CONTENT_TYPE = "image/jpeg"


class InMemoryThumbnailCache:
    def __init__(self, max_size: int = MAX_CACHE_SIZE):
        self._entries: OrderedDict[UploadID, bytes] = OrderedDict()
        self._max_size = max_size
        self._lock = threading.Lock()

    def get(self, upload_id: UploadID) -> bytes | None:
        with self._lock:
            if upload_id not in self._entries:
                return None
            self._entries.move_to_end(upload_id)
            return self._entries[upload_id]

    def set(self, upload_id: UploadID, value: bytes) -> None:
        with self._lock:
            self._entries[upload_id] = value
            self._entries.move_to_end(upload_id)
            if len(self._entries) > self._max_size:
                self._entries.popitem(last=False)

    def evict(self, upload_id: UploadID) -> None:
        with self._lock:
            self._entries.pop(upload_id, None)


class InMemoryThumbnailService:
    def __init__(self, cache: InMemoryThumbnailCache, max_dimension: int = MAX_DIMENSION):
        self._cache = cache
        self._max_dimension = max_dimension

    def get_thumbnail(self, upload_id: UploadID, content: bytes) -> Thumbnail:
        # Concurrent misses for the same id regenerate independently, and a
        # concurrent evict may race with the trailing cache.set. Both are
        # acceptable here since the route deletes metadata before evicting,
        # so a stale entry is never served.
        cached = self._cache.get(upload_id)
        if cached is None:
            cached = self._generate_thumbnail(content)
            self._cache.set(upload_id, cached)
        return Thumbnail(content=cached, content_type=THUMBNAIL_CONTENT_TYPE)

    def evict(self, upload_id: UploadID) -> None:
        self._cache.evict(upload_id)

    def _generate_thumbnail(self, content: bytes) -> bytes:
        try:
            image = Image.open(io.BytesIO(content))
            image.thumbnail((self._max_dimension, self._max_dimension))
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
            raise InvalidImageException() from exc

        if image.mode != "RGB":
            image = image.convert("RGB")

        output = io.BytesIO()
        image.save(output, format="JPEG")
        return output.getvalue()
