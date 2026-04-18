from fastapi.testclient import TestClient

from lenzr_server.main import app

client = TestClient(app)


def test__openapi__just_call__returns_200_and_json():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()


def test__openapi__includes_upload_created_webhook(client):
    schema = client.get("/openapi.json").json()

    webhooks = schema.get("webhooks", {})
    assert "upload.created" in webhooks
    assert "post" in webhooks["upload.created"]
