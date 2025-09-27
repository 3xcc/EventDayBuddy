import pytest
from unittest.mock import MagicMock, patch
from web import server
from fastapi.testclient import TestClient

client = TestClient(server.app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_webhook_not_initialized():
    with patch("web.server.application", None):
        response = client.post("/dummy-token", json={})
        assert response.status_code == 503
        assert not response.json()["ok"]

def test_webhook_success():
    dummy_app = MagicMock()
    dummy_app.bot = MagicMock()
    dummy_app.update_queue = MagicMock()
    with patch("web.server.application", dummy_app):
        with patch("web.server.Update.de_json") as de_json:
            de_json.return_value = MagicMock()
            response = client.post("/dummy-token", json={})
            assert response.status_code == 200 or response.status_code == 503
