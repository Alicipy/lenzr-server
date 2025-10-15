import pytest
from fastapi.testclient import TestClient

from lenzr_server import models
from lenzr_server.main import app, engine, get_id_creator
from lenzr_server.upload_id_creators.counting_id_creator import CountingIdCreator

client = TestClient(app)


creator = CountingIdCreator()
def counting_id_creator():
    return creator

app.dependency_overrides[get_id_creator] = counting_id_creator

@pytest.fixture(autouse=True)
def reset_counter():
    creator.id = 0

@pytest.fixture(autouse=True)
def clean_db():
    models.SQLModel.metadata.create_all(engine)
    yield
    models.SQLModel.metadata.drop_all(engine)


def test__api_put_upload__upload_image_file__returns_201_with_id():
    response = client.put("/uploads", files={"upload": ("test.png", b"Hello, world!", "image/png")})
    assert response.status_code == 201
    assert "upload_id" in response.json()
    assert response.json()["upload_id"] == "1"

def test__api_put_upload__upload_txt_file__returns_400_bad_request():
    response = client.put("/uploads", files={"upload": ("test.txt", b"Hello, world!", "text/plain")})
    assert response.status_code == 400
    assert response.json()["detail"] == "Bad request - invalid file"

def test__api_put_upload__upload_no_file_type__returns_400_bad_request():
    response = client.put("/uploads", files={"upload": ("test", b"Hello, world!")})
    assert response.status_code == 400

def test__api_put_upload__upload_no_file__returns_422_validation_error():
    response = client.put("/uploads")
    assert response.status_code == 422

def test__api_get_upload_upload_id___get_upload_after_put_with_id__returns_200_with_data():
    # Create a sample image file
    response = client.put("/uploads", 
                         files={"upload": ("test.png", b"Hello, world!", "image/png")})
    response.raise_for_status()
    upload_id = response.json()["upload_id"]

    response = client.get(f"/uploads/{upload_id}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == b"Hello, world!"

def test__api_get_upload_upload_id__get_upload_with_invalid_id__returns_404():
    response = client.get("/uploads/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Upload not found"

def test__api_get_uploads__get_uploads_after_put_multiple_files__returns_200_with_ids():
    response = client.put("/uploads", 
                         files={"upload": ("test1.png", b"File 1", "image/png")})
    response.raise_for_status()
    response = client.put("/uploads", 
                         files={"upload": ("test2.jpg", b"File 2", "image/jpeg")})
    response.raise_for_status()

    response = client.get("/uploads")

    assert response.status_code == 200
    assert "uploads" in response.json()
    assert set(response.json()["uploads"]) == {"1", "2"}

def test__api_get_uploads__get_uploads_with_no_files__returns_200_with_empty_list():
    response = client.get("/uploads")

    assert response.status_code == 200
    assert "uploads" in response.json()
    assert response.json()["uploads"] == []