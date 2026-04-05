import io
import threading

from PIL import Image

from lenzr_server.thumbnail_service import MAX_DIMENSION, ThumbnailService


def _create_test_image(width: int, height: int, image_format: str = "PNG") -> bytes:
    image = Image.new("RGB", (width, height), color="red")
    output = io.BytesIO()
    image.save(output, format=image_format)
    return output.getvalue()


def test__get_thumbnail__large_image__resizes_to_max_dimension():
    service = ThumbnailService()
    original = _create_test_image(800, 600)

    thumbnail_bytes = service.get_thumbnail("upload1", lambda: original)

    thumb = Image.open(io.BytesIO(thumbnail_bytes))
    assert max(thumb.size) == MAX_DIMENSION
    assert thumb.format == "JPEG"


def test__get_thumbnail__small_image__does_not_upscale():
    service = ThumbnailService()
    original = _create_test_image(100, 80)

    thumbnail_bytes = service.get_thumbnail("upload1", lambda: original)

    thumb = Image.open(io.BytesIO(thumbnail_bytes))
    assert thumb.size == (100, 80)


def test__get_thumbnail__preserves_aspect_ratio():
    service = ThumbnailService()
    original = _create_test_image(1000, 500)

    thumbnail_bytes = service.get_thumbnail("upload1", lambda: original)

    thumb = Image.open(io.BytesIO(thumbnail_bytes))
    assert thumb.size == (MAX_DIMENSION, 100)


def test__get_thumbnail__caches_result():
    service = ThumbnailService()
    original = _create_test_image(800, 600)

    first = service.get_thumbnail("upload1", lambda: original)
    # Pass different loader — should still return cached version
    second = service.get_thumbnail("upload1", lambda: _create_test_image(400, 300))

    assert first == second


def test__get_thumbnail__different_ids__separate_cache_entries():
    service = ThumbnailService()
    img1 = _create_test_image(100, 100)
    img2 = _create_test_image(50, 50)

    thumb1 = service.get_thumbnail("upload1", lambda: img1)
    thumb2 = service.get_thumbnail("upload2", lambda: img2)

    assert thumb1 != thumb2


def test__evict__removes_cache_entry():
    service = ThumbnailService()
    original = _create_test_image(800, 600)

    service.get_thumbnail("upload1", lambda: original)
    service.evict("upload1")

    # After eviction, a new thumbnail is generated from new content
    different = _create_test_image(100, 80)
    thumb = service.get_thumbnail("upload1", lambda: different)
    new_thumb = Image.open(io.BytesIO(thumb))
    assert new_thumb.size == (100, 80)


def test__evict__nonexistent_id__no_error():
    service = ThumbnailService()
    service.evict("nonexistent")


def test__get_thumbnail__exceeds_max_cache_size__evicts_lru_entry():
    service = ThumbnailService(max_cache_size=2)
    img1 = _create_test_image(100, 100)
    img2 = _create_test_image(200, 200)
    img3 = _create_test_image(300, 300)

    service.get_thumbnail("upload1", lambda: img1)
    service.get_thumbnail("upload2", lambda: img2)
    service.get_thumbnail("upload3", lambda: img3)

    # upload1 (LRU) should have been evicted
    assert "upload1" not in service._cache
    assert "upload2" in service._cache
    assert "upload3" in service._cache


def test__get_thumbnail__cache_hit_refreshes_lru_order():
    service = ThumbnailService(max_cache_size=2)
    img1 = _create_test_image(100, 100)
    img2 = _create_test_image(200, 200)
    img3 = _create_test_image(300, 300)

    service.get_thumbnail("upload1", lambda: img1)
    service.get_thumbnail("upload2", lambda: img2)
    # Access upload1 again — moves it to most-recently-used
    service.get_thumbnail("upload1", lambda: img1)
    # This should evict upload2 (now LRU), not upload1
    service.get_thumbnail("upload3", lambda: img3)

    assert "upload1" in service._cache
    assert "upload2" not in service._cache
    assert "upload3" in service._cache


def test__concurrent_get_and_evict__no_errors():
    service = ThumbnailService(max_cache_size=5)
    images = [_create_test_image(100 + i * 10, 100 + i * 10) for i in range(10)]
    errors: list[Exception] = []

    def worker(i: int):
        try:
            upload_id = f"upload{i % 5}"
            service.get_thumbnail(upload_id, lambda i=i: images[i % len(images)])
            if i % 3 == 0:
                service.evict(upload_id)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []


def test__get_thumbnail__rgba_image__converts_to_rgb_jpeg():
    service = ThumbnailService()
    image = Image.new("RGBA", (400, 400), color=(255, 0, 0, 128))
    output = io.BytesIO()
    image.save(output, format="PNG")
    original = output.getvalue()

    thumbnail_bytes = service.get_thumbnail("upload1", lambda: original)

    thumb = Image.open(io.BytesIO(thumbnail_bytes))
    assert thumb.mode == "RGB"
    assert thumb.format == "JPEG"
