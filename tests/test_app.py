import base64
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlmodel import SQLModel

from lenzr_server.db import engine
from lenzr_server.dependencies import get_id_creator
from lenzr_server.main import app
from lenzr_server.upload_id_creators.counting_id_creator import CountingIdCreator

creator = CountingIdCreator()


def counting_id_creator():
    return creator


app.dependency_overrides[get_id_creator] = counting_id_creator


@pytest.fixture(autouse=True)
def reset_creator():
    creator.reset()


@pytest.fixture(autouse=True)
def clean_db():
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)


def get_auth_headers(username: str = "test_user", password: str = "test_pass"):
    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {credentials}"}


def _create_upload(
    client: TestClient, content: bytes = b"Hello, world!", filename: str = "test.png"
) -> str:
    response = client.post(
        "/uploads",
        files={"upload": (filename, content, "image/png")},
        headers=get_auth_headers(),
    )
    response.raise_for_status()
    return response.json()["upload_id"]


def _create_real_image(width: int = 800, height: int = 600) -> bytes:
    image = Image.new("RGB", (width, height), color="blue")
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test__api_post_upload__upload_image_file__returns_201_with_id(client):
    response = client.post(
        "/uploads",
        files={"upload": ("test.png", b"Hello, world!", "image/png")},
        headers=get_auth_headers(),
    )
    assert response.status_code == 201
    assert "upload_id" in response.json()
    assert response.json()["upload_id"] == "1"


def test__api_post_upload__upload_image_file_twice__returns_201_and_200_with_id(client):
    response1 = client.post(
        "/uploads",
        files={"upload": ("test.png", b"Hello, world!", "image/png")},
        headers=get_auth_headers(),
    )
    response2 = client.post(
        "/uploads",
        files={"upload": ("test.png", b"Hello, world!", "image/png")},
        headers=get_auth_headers(),
    )

    assert response2.status_code == 200
    assert response1.json()["upload_id"] == response2.json()["upload_id"]


def test__api_post_upload__upload_image_file_without_auth__returns_401_unauthorized(client):
    response = client.post(
        "/uploads", files={"upload": ("test.png", b"Hello, world!", "image/png")}
    )
    assert response.status_code == 401


def test__api_post_upload__upload_txt_file__returns_400_bad_request(client):
    response = client.post(
        "/uploads",
        files={"upload": ("test.txt", b"Hello, world!", "text/plain")},
        headers=get_auth_headers(),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Bad request - invalid file"


def test__api_post_upload__upload_no_file_type__returns_400_bad_request(client):
    response = client.post(
        "/uploads", files={"upload": ("test", b"Hello, world!")}, headers=get_auth_headers()
    )
    assert response.status_code == 400


def test__api_post_upload__upload_no_file__returns_422_validation_error(client):
    response = client.post("/uploads", headers=get_auth_headers())
    assert response.status_code == 422


def test__api_get_upload_upload_id___get_upload_after_post_with_id__returns_200_with_data(client):
    response = client.post(
        "/uploads",
        files={"upload": ("test.png", b"Hello, world!", "image/png")},
        headers=get_auth_headers(),
    )
    response.raise_for_status()
    upload_id = response.json()["upload_id"]

    response = client.get(f"/uploads/{upload_id}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == b"Hello, world!"


def test__api_get_upload_upload_id__get_upload_with_invalid_id__returns_404(client):
    response = client.get("/uploads/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Upload not found"


def test_api_delete_upload_upload_id__delete_upload_after_post_id__returns_200(client):
    response = client.post(
        "/uploads",
        files={"upload": ("test.png", b"Hello, world!", "image/png")},
        headers=get_auth_headers(),
    )
    response.raise_for_status()
    upload_id = response.json()["upload_id"]

    response = client.delete(f"/uploads/{upload_id}", headers=get_auth_headers())
    assert response.status_code == 200


def test_api_delete_upload_upload_id__delete_nonexistent_upload_returns_404(client):
    client.post(
        "/uploads",
        files={"upload": ("test.png", b"Hello, world!", "image/png")},
        headers=get_auth_headers(),
    )

    response = client.delete("/uploads/123", headers=get_auth_headers())
    assert response.status_code == 404
    assert response.json()["detail"] == "Upload not found"


def test_api_delete_upload_upload_id__without_auth__returns_401(client):
    response = client.post(
        "/uploads",
        files={"upload": ("test.png", b"Hello, world!", "image/png")},
        headers=get_auth_headers(),
    )
    upload_id = response.json()["upload_id"]

    response = client.delete(f"/uploads/{upload_id}")
    assert response.status_code == 401


def test__api_get_uploads__get_uploads_after_post_multiple_files__returns_200_with_ids(client):
    response = client.post(
        "/uploads",
        files={"upload": ("test1.png", b"File 1", "image/png")},
        headers=get_auth_headers(),
    )
    response.raise_for_status()
    response = client.post(
        "/uploads",
        files={"upload": ("test2.jpg", b"File 2", "image/jpeg")},
        headers=get_auth_headers(),
    )
    response.raise_for_status()

    response = client.get("/uploads", headers=get_auth_headers())

    assert response.status_code == 200
    content = response.json()
    assert {"upload_id": "1"} in content
    assert {"upload_id": "2"} in content


def test__api_get_uploads__get_uploads_without_auth__returns_401_unauthorized(client):
    response = client.get("/uploads")
    assert response.status_code == 401


def test__api_get_uploads__get_uploads_with_no_files__returns_200_with_empty_list(client):
    response = client.get("/uploads", headers=get_auth_headers())

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize(
    "offset,limit,expected_upload_ids",
    [
        pytest.param(None, None, {"5", "4", "3", "2", "1"}, id="all_default"),
        pytest.param(None, 2, {"5", "4"}, id="default_offset"),
        pytest.param(2, None, {"3", "2", "1"}, id="default_limit"),
        pytest.param(1, 3, {"4", "3", "2"}, id="both_set"),
    ],
)
def test__api_get_uploads__pagination(
    client, offset: int | None, limit: int | None, expected_upload_ids: set[str]
):
    for i in range(5):
        response = client.post(
            "/uploads",
            files={"upload": (f"test{i}.png", f"File {i}".encode(), "image/png")},
            headers=get_auth_headers(),
        )
        response.raise_for_status()

    query_params = {}
    if limit is not None:
        query_params["limit"] = limit
    if offset is not None:
        query_params["offset"] = offset

    response = client.get("/uploads", headers=get_auth_headers(), params=query_params)

    assert response.status_code == 200
    upload_ids = {upload["upload_id"] for upload in response.json()}
    assert upload_ids == expected_upload_ids


def test__api_put_upload_tags__set_tags__returns_200_with_tags(client):
    upload_id = _create_upload(client)

    response = client.put(
        f"/uploads/{upload_id}/tags",
        json={"tags": ["landscape", "nature"]},
        headers=get_auth_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["upload_id"] == upload_id
    assert sorted(data["tags"]) == ["landscape", "nature"]
    assert "created_at" in data
    assert data["content_type"] == "image/png"


def test__api_put_upload_tags__nonexistent_upload__returns_404(client):
    response = client.put(
        "/uploads/nonexistent/tags",
        json={"tags": ["landscape"]},
        headers=get_auth_headers(),
    )

    assert response.status_code == 404


def test__api_put_upload_tags__without_auth__returns_401(client):
    upload_id = _create_upload(client)

    response = client.put(
        f"/uploads/{upload_id}/tags",
        json={"tags": ["landscape"]},
    )

    assert response.status_code == 401


def test__api_put_upload_tags__invalid_tag_name__returns_422(client):
    upload_id = _create_upload(client)

    response = client.put(
        f"/uploads/{upload_id}/tags",
        json={"tags": ["INVALID"]},
        headers=get_auth_headers(),
    )

    assert response.status_code == 422


def test__api_get_upload_tags__returns_200_with_tags(client):
    upload_id = _create_upload(client)
    client.put(
        f"/uploads/{upload_id}/tags",
        json={"tags": ["landscape", "nature"]},
        headers=get_auth_headers(),
    )

    response = client.get(
        f"/uploads/{upload_id}/tags",
        headers=get_auth_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["upload_id"] == upload_id
    assert sorted(data["tags"]) == ["landscape", "nature"]
    assert "created_at" in data
    assert data["content_type"] == "image/png"


def test__api_get_upload_tags__no_tags__returns_200_with_empty_list(client):
    upload_id = _create_upload(client)

    response = client.get(
        f"/uploads/{upload_id}/tags",
        headers=get_auth_headers(),
    )

    assert response.status_code == 200
    assert response.json()["tags"] == []


def test__api_get_upload_tags__nonexistent_upload__returns_404(client):
    response = client.get(
        "/uploads/nonexistent/tags",
        headers=get_auth_headers(),
    )

    assert response.status_code == 404


def test__api_get_upload_tags__without_auth__returns_401(client):
    upload_id = _create_upload(client)

    response = client.get(f"/uploads/{upload_id}/tags")

    assert response.status_code == 401


def test__api_put_upload_tags__replace_tags__get_reflects_new_tags(client):
    upload_id = _create_upload(client)

    client.put(
        f"/uploads/{upload_id}/tags",
        json={"tags": ["landscape", "nature"]},
        headers=get_auth_headers(),
    )
    client.put(
        f"/uploads/{upload_id}/tags",
        json={"tags": ["urban", "night"]},
        headers=get_auth_headers(),
    )

    response = client.get(
        f"/uploads/{upload_id}/tags",
        headers=get_auth_headers(),
    )

    assert response.status_code == 200
    assert sorted(response.json()["tags"]) == ["night", "urban"]


def test__api_put_upload_tags__empty_list__clears_tags(client):
    upload_id = _create_upload(client)

    client.put(
        f"/uploads/{upload_id}/tags",
        json={"tags": ["landscape"]},
        headers=get_auth_headers(),
    )
    response = client.put(
        f"/uploads/{upload_id}/tags",
        json={"tags": []},
        headers=get_auth_headers(),
    )

    assert response.status_code == 200
    assert response.json()["tags"] == []

    get_response = client.get(
        f"/uploads/{upload_id}/tags",
        headers=get_auth_headers(),
    )
    assert get_response.json()["tags"] == []


def test__api_get_uploads_search__and_logic__returns_matching_uploads(client):
    upload_id1 = _create_upload(client, b"file1", "f1.png")
    upload_id2 = _create_upload(client, b"file2", "f2.png")

    client.put(
        f"/uploads/{upload_id1}/tags",
        json={"tags": ["landscape", "nature"]},
        headers=get_auth_headers(),
    )
    client.put(
        f"/uploads/{upload_id2}/tags",
        json={"tags": ["landscape", "urban"]},
        headers=get_auth_headers(),
    )

    response = client.get(
        "/uploads/search",
        params={"tags": ["landscape", "nature"]},
        headers=get_auth_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["upload_id"] == upload_id1


def test__api_get_uploads_search__and_logic__response_includes_all_tags(client):
    upload_id1 = _create_upload(client, b"file1", "f1.png")
    _create_upload(client, b"file2", "f2.png")

    client.put(
        f"/uploads/{upload_id1}/tags",
        json={"tags": ["landscape", "nature", "sunset"]},
        headers=get_auth_headers(),
    )

    response = client.get(
        "/uploads/search",
        params={"tags": ["landscape", "nature"]},
        headers=get_auth_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["upload_id"] == upload_id1
    assert sorted(data[0]["tags"]) == ["landscape", "nature", "sunset"]
    assert "created_at" in data[0]
    assert data[0]["content_type"] == "image/png"


def test__api_get_uploads_search__single_tag__returns_all_matching(client):
    upload_id1 = _create_upload(client, b"file1", "f1.png")
    upload_id2 = _create_upload(client, b"file2", "f2.png")

    client.put(
        f"/uploads/{upload_id1}/tags",
        json={"tags": ["landscape"]},
        headers=get_auth_headers(),
    )
    client.put(
        f"/uploads/{upload_id2}/tags",
        json={"tags": ["landscape"]},
        headers=get_auth_headers(),
    )

    response = client.get(
        "/uploads/search",
        params={"tags": ["landscape"]},
        headers=get_auth_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test__api_get_uploads_search__invalid_tag_name__returns_422(client):
    response = client.get(
        "/uploads/search",
        params={"tags": ["INVALID"]},
        headers=get_auth_headers(),
    )

    assert response.status_code == 422


def test__api_get_uploads_search__no_matches__returns_empty(client):
    _create_upload(client)

    response = client.get(
        "/uploads/search",
        params={"tags": ["nonexistent"]},
        headers=get_auth_headers(),
    )

    assert response.status_code == 200
    assert response.json() == []


def test__api_get_uploads_search__without_auth__returns_401(client):
    response = client.get(
        "/uploads/search",
        params={"tags": ["landscape"]},
    )

    assert response.status_code == 401


def test__api_get_tags__returns_all_tags(client):
    upload_id1 = _create_upload(client, b"file1", "f1.png")
    upload_id2 = _create_upload(client, b"file2", "f2.png")

    client.put(
        f"/uploads/{upload_id1}/tags",
        json={"tags": ["nature", "landscape"]},
        headers=get_auth_headers(),
    )
    client.put(
        f"/uploads/{upload_id2}/tags",
        json={"tags": ["urban"]},
        headers=get_auth_headers(),
    )

    response = client.get("/tags", headers=get_auth_headers())

    assert response.status_code == 200
    assert response.json()["tags"] == ["landscape", "nature", "urban"]


def test__api_get_tags__empty__returns_empty(client):
    response = client.get("/tags", headers=get_auth_headers())

    assert response.status_code == 200
    assert response.json()["tags"] == []


def test__api_get_tags__without_auth__returns_401(client):
    response = client.get("/tags")

    assert response.status_code == 401


def test__api_post_upload__with_tags__returns_201_with_tags(client):
    response = client.post(
        "/uploads",
        files={"upload": ("test.png", b"Hello, world!", "image/png")},
        params={"tags": ["landscape", "nature"]},
        headers=get_auth_headers(),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["upload_id"] == "1"
    assert sorted(data["tags"]) == ["landscape", "nature"]


def test__api_post_upload__with_tags__tags_are_persisted(client):
    response = client.post(
        "/uploads",
        files={"upload": ("test.png", b"Hello, world!", "image/png")},
        params={"tags": ["landscape", "nature"]},
        headers=get_auth_headers(),
    )
    upload_id = response.json()["upload_id"]

    tags_response = client.get(
        f"/uploads/{upload_id}/tags",
        headers=get_auth_headers(),
    )

    assert tags_response.status_code == 200
    assert sorted(tags_response.json()["tags"]) == ["landscape", "nature"]


def test__api_post_upload__without_tags__returns_201_with_empty_tags(client):
    response = client.post(
        "/uploads",
        files={"upload": ("test.png", b"Hello, world!", "image/png")},
        headers=get_auth_headers(),
    )

    assert response.status_code == 201
    assert response.json()["tags"] == []


def test__api_post_upload__duplicate_with_tags__returns_200_without_tags(client):
    client.post(
        "/uploads",
        files={"upload": ("test.png", b"Hello, world!", "image/png")},
        params={"tags": ["landscape"]},
        headers=get_auth_headers(),
    )

    response = client.post(
        "/uploads",
        files={"upload": ("test.png", b"Hello, world!", "image/png")},
        params={"tags": ["nature"]},
        headers=get_auth_headers(),
    )

    assert response.status_code == 200
    assert response.json()["tags"] == []


def test__api_post_upload__with_invalid_tags__returns_422(client):
    response = client.post(
        "/uploads",
        files={"upload": ("test.png", b"Hello, world!", "image/png")},
        params={"tags": ["INVALID"]},
        headers=get_auth_headers(),
    )

    assert response.status_code == 422


def test__api_post_upload__with_duplicate_tags__persists_deduplicated(client):
    response = client.post(
        "/uploads",
        files={"upload": ("test.png", b"Hello, world!", "image/png")},
        params={"tags": ["landscape", "landscape", "nature"]},
        headers=get_auth_headers(),
    )

    assert response.status_code == 201
    upload_id = response.json()["upload_id"]

    tags_response = client.get(
        f"/uploads/{upload_id}/tags",
        headers=get_auth_headers(),
    )

    assert sorted(tags_response.json()["tags"]) == ["landscape", "nature"]


def test__api_get_upload_thumbnail__valid_upload__returns_200_jpeg(client):
    upload_id = _create_upload(client, _create_real_image(), "photo.png")

    response = client.get(f"/uploads/{upload_id}/thumbnail")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    thumb = Image.open(io.BytesIO(response.content))
    assert max(thumb.size) == 200


def test__api_get_upload_thumbnail__nonexistent_upload__returns_404(client):
    response = client.get("/uploads/nonexistent/thumbnail")

    assert response.status_code == 404


def test__api_get_upload_thumbnail__cached_on_second_request__same_content(client):
    upload_id = _create_upload(client, _create_real_image(), "photo.png")

    first = client.get(f"/uploads/{upload_id}/thumbnail")
    second = client.get(f"/uploads/{upload_id}/thumbnail")

    assert first.content == second.content


def test__api_get_upload_thumbnail__after_delete__returns_404(client):
    upload_id = _create_upload(client, _create_real_image(), "photo.png")

    client.get(f"/uploads/{upload_id}/thumbnail")
    client.delete(f"/uploads/{upload_id}", headers=get_auth_headers())

    response = client.get(f"/uploads/{upload_id}/thumbnail")
    assert response.status_code == 404


def test__api_get_upload_thumbnail__corrupted_image_bytes__returns_422(client):
    upload_id = _create_upload(client, b"not an image", "broken.png")

    response = client.get(f"/uploads/{upload_id}/thumbnail")

    assert response.status_code == 422
