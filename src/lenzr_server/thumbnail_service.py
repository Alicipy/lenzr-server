import io
import threading
from collections import OrderedDict
from collections.abc import Callable

from PIL import Image

from lenzr_server.types import UploadID

MAX_DIMENSION = 200
MAX_CACHE_SIZE = 1000
THUMBNAIL_CONTENT_TYPE = "image/jpeg"


class ThumbnailService:
    def __init__(self, max_cache_size: int = MAX_CACHE_SIZE):
        self._cache: OrderedDict[UploadID, bytes] = OrderedDict()
        self._max_cache_size = max_cache_size
        # A single lock for all cache operations. Cache hits (dict lookup +
        # move_to_end) and generation (200px resize) are fast enough that a
        # reader/writer lock wouldn't meaningfully improve concurrency here.
        self._lock = threading.Lock()

    def get_thumbnail(self, upload_id: UploadID, load_content: Callable[[], bytes]) -> bytes:
        with self._lock:
            if upload_id in self._cache:
                self._cache.move_to_end(upload_id)
                return self._cache[upload_id]

            thumbnail_bytes = self._generate_thumbnail(load_content())
            self._cache[upload_id] = thumbnail_bytes
            if len(self._cache) > self._max_cache_size:
                self._cache.popitem(last=False)
            return thumbnail_bytes

    def evict(self, upload_id: UploadID) -> None:
        with self._lock:
            self._cache.pop(upload_id, None)

    def _generate_thumbnail(self, content: bytes) -> bytes:
        image = Image.open(io.BytesIO(content))
        image.thumbnail((MAX_DIMENSION, MAX_DIMENSION))

        if image.mode != "RGB":
            image = image.convert("RGB")

        output = io.BytesIO()
        image.save(output, format="JPEG")
        return output.getvalue()
