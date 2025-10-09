from fastapi.testclient import TestClient

from lenzr_server.main import app

client = TestClient(app)


def test__openapi__just_call__returns_200_and_json():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()

