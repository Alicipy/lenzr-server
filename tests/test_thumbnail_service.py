import io
import threading

import pytest
from PIL import Image

from lenzr_server.thumbnail_service import (
    InMemoryThumbnailCache,
    InMemoryThumbnailService,
    InvalidImageException,
)

TEST_MAX_DIMENSION = 100


@pytest.fixture
def sized_service(thumbnail_cache) -> InMemoryThumbnailService:
    return InMemoryThumbnailService(cache=thumbnail_cache, max_dimension=TEST_MAX_DIMENSION)


@pytest.mark.parametrize(
    "source_size,expected_size",
    [
        pytest.param((800, 600), (TEST_MAX_DIMENSION, 75), id="downscales_wide"),
        pytest.param((600, 800), (75, TEST_MAX_DIMENSION), id="downscales_tall"),
        pytest.param((50, 40), (50, 40), id="preserves_small"),
        pytest.param((1000, 500), (TEST_MAX_DIMENSION, 50), id="preserves_aspect_ratio_wide"),
        pytest.param((500, 1000), (50, TEST_MAX_DIMENSION), id="preserves_aspect_ratio_tall"),
    ],
)
def test__get_thumbnail__sizing(sized_service, create_test_image, source_size, expected_size):
    original = create_test_image(*source_size)

    thumbnail = sized_service.get_thumbnail("upload1", original)

    thumb = Image.open(io.BytesIO(thumbnail.content))
    assert thumb.size == expected_size
    assert thumb.format == "JPEG"
    assert thumbnail.content_type == "image/jpeg"


@pytest.mark.parametrize(
    "source_size,expected_size",
    [
        pytest.param((800, 400), (200, 100), id="wide"),
        pytest.param((400, 800), (100, 200), id="tall"),
    ],
)
def test__get_thumbnail__default_max_dimension(
    thumbnail_service, create_test_image, source_size, expected_size
):
    original = create_test_image(*source_size)

    thumbnail = thumbnail_service.get_thumbnail("upload1", original)

    thumb = Image.open(io.BytesIO(thumbnail.content))
    assert thumb.size == expected_size


def test__get_thumbnail__caches_result(thumbnail_service, create_test_image):
    original = create_test_image(800, 600)
    other = create_test_image(400, 300)

    first = thumbnail_service.get_thumbnail("upload1", original)
    second = thumbnail_service.get_thumbnail("upload1", other)

    assert first.content == second.content


def test__get_thumbnail__different_ids__separate_cache_entries(
    thumbnail_service, create_test_image
):
    img1 = create_test_image(100, 100)
    img2 = create_test_image(50, 50)

    thumb1 = thumbnail_service.get_thumbnail("upload1", img1)
    thumb2 = thumbnail_service.get_thumbnail("upload2", img2)

    assert thumb1.content != thumb2.content


def test__evict__removes_cache_entry(thumbnail_service, create_test_image):
    original = create_test_image(800, 600)
    thumbnail_service.get_thumbnail("upload1", original)
    thumbnail_service.evict("upload1")

    different = create_test_image(100, 80)
    thumb = thumbnail_service.get_thumbnail("upload1", different)
    assert Image.open(io.BytesIO(thumb.content)).size == (100, 80)


def test__evict__nonexistent_id__no_error(thumbnail_service):
    thumbnail_service.evict("nonexistent")


def test__get_thumbnail__exceeds_max_cache_size__evicts_lru_entry(create_test_image):
    cache = InMemoryThumbnailCache(max_size=2)
    service = InMemoryThumbnailService(cache=cache)
    service.get_thumbnail("upload1", create_test_image(100, 100))
    service.get_thumbnail("upload2", create_test_image(200, 200))
    service.get_thumbnail("upload3", create_test_image(300, 300))

    assert cache.get("upload1") is None
    assert cache.get("upload2") is not None
    assert cache.get("upload3") is not None


def test__get_thumbnail__cache_hit_refreshes_lru_order(create_test_image):
    cache = InMemoryThumbnailCache(max_size=2)
    service = InMemoryThumbnailService(cache=cache)

    service.get_thumbnail("upload1", create_test_image(100, 100))
    service.get_thumbnail("upload2", create_test_image(200, 200))
    # Access upload1 — moves it to most-recently-used
    service.get_thumbnail("upload1", create_test_image(100, 100))
    # Inserting upload3 should evict upload2, not upload1
    service.get_thumbnail("upload3", create_test_image(300, 300))

    assert cache.get("upload1") is not None
    assert cache.get("upload2") is None
    assert cache.get("upload3") is not None


def test__concurrent_get_and_evict__no_errors(create_test_image):
    service = InMemoryThumbnailService(cache=InMemoryThumbnailCache(max_size=5))
    images = [create_test_image(100 + i * 10, 100 + i * 10) for i in range(10)]
    errors: list[Exception] = []

    def worker(i: int):
        try:
            upload_id = f"upload{i % 5}"
            service.get_thumbnail(upload_id, images[i % len(images)])
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


def test__get_thumbnail__rgba_image__converts_to_rgb_jpeg(thumbnail_service, create_test_image):
    original = create_test_image(400, 400, mode="RGBA", color=(255, 0, 0, 128))

    thumbnail = thumbnail_service.get_thumbnail("upload1", original)

    thumb = Image.open(io.BytesIO(thumbnail.content))
    assert thumb.mode == "RGB"
    assert thumb.format == "JPEG"


@pytest.mark.parametrize(
    "mode,color,image_format",
    [
        pytest.param("L", 128, "PNG", id="grayscale"),
        pytest.param("LA", (128, 200), "PNG", id="grayscale_with_alpha"),
        pytest.param("P", 5, "PNG", id="palette"),
        pytest.param("CMYK", (0, 128, 255, 64), "JPEG", id="cmyk"),
    ],
)
def test__get_thumbnail__non_rgb_modes__converts_to_rgb_jpeg(
    thumbnail_service, create_test_image, mode, color, image_format
):
    original = create_test_image(400, 400, image_format=image_format, mode=mode, color=color)

    thumbnail = thumbnail_service.get_thumbnail("upload1", original)

    thumb = Image.open(io.BytesIO(thumbnail.content))
    assert thumb.mode == "RGB"
    assert thumb.format == "JPEG"


def test__get_thumbnail__corrupted_bytes__raises_invalid_image(thumbnail_service):
    with pytest.raises(InvalidImageException):
        thumbnail_service.get_thumbnail("upload1", b"not an image")


def test__get_thumbnail__truncated_bytes__raises_invalid_image(
    thumbnail_service, create_test_image
):
    truncated = create_test_image(400, 400)[:50]

    with pytest.raises(InvalidImageException):
        thumbnail_service.get_thumbnail("upload1", truncated)


def test__get_thumbnail__decompression_bomb__raises_invalid_image(
    thumbnail_service, create_test_image, monkeypatch
):
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 100)
    oversized = create_test_image(400, 400)

    with pytest.raises(InvalidImageException):
        thumbnail_service.get_thumbnail("upload1", oversized)
