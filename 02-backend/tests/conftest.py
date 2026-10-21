import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def client():
    settings = Settings(_env_file=None, jwt_secret_key="test-key-with-at-least-32-characters")
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def headers(client):
    response = client.post(
        "/api/auth/login", json={"email": "alfa-hack-2026", "password": "password123"}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
