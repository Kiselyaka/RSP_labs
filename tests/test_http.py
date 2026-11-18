from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import uuid4
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from internal.controller.resource_controller import survey_service, user_service
from internal.domain.errors import ErrAlreadyExists, ErrConflict, ErrInvalidInput, ErrNotFound
from internal.domain.models import User

spec = spec_from_file_location("lab7_application", Path(__file__).resolve().parents[1] / "cmd/app/main.py")
application = module_from_spec(spec)
spec.loader.exec_module(application)
app = application.app


@pytest.fixture
def client():
    users, surveys = Mock(), Mock()
    app.dependency_overrides[user_service] = lambda: users
    app.dependency_overrides[survey_service] = lambda: surveys
    # No lifespan: tests inject services and never start PostgreSQL.
    test_client = TestClient(app, raise_server_exceptions=False)
    try:
        yield test_client, users, surveys
    finally:
        test_client.close()
        app.dependency_overrides.clear()


def make_user():
    return User(id=uuid4(), email="demo@example.test", password_hash="secret-hash",
                display_name="Demo", created_at=datetime.now(timezone.utc))


def test_create_returns_location_and_safe_dto(client):
    http, users, _ = client
    user = make_user()
    users.create.return_value = user
    response = http.post("/api/v1/users", json={
        "email": user.email, "password": "DemoPassword123", "displayName": "Demo",
    })
    assert response.status_code == 201
    assert response.headers["location"] == f"/api/v1/users/{user.id}"
    assert response.json()["displayName"] == "Demo"
    assert "password" not in response.text and "secret-hash" not in response.text


@pytest.mark.parametrize("error,status", [
    (ErrNotFound("Missing"), 404), (ErrAlreadyExists("Duplicate"), 409),
    (ErrConflict("Related record"), 409), (ErrInvalidInput("Invalid"), 400),
])
def test_domain_errors_use_common_response(client, error, status):
    http, users, _ = client
    users.get.side_effect = error
    response = http.get(f"/api/v1/users/{uuid4()}")
    assert response.status_code == status
    assert set(response.json()) == {"code", "message", "timestamp"}


def test_delete_returns_empty_body(client):
    http, _, _ = client
    response = http.delete(f"/api/v1/users/{uuid4()}")
    assert response.status_code == 204 and response.content == b""


def test_invalid_uuid_and_body_return_400(client):
    http, _, _ = client
    assert http.get("/api/v1/users/not-a-uuid").status_code == 400
    response = http.post("/api/v1/users", json={"password": "sensitive"})
    assert response.status_code == 400 and "sensitive" not in response.text


def test_unexpected_failure_is_sanitized(client):
    http, users, _ = client
    users.get.side_effect = RuntimeError("private database details")
    response = http.get(f"/api/v1/users/{uuid4()}")
    assert response.status_code == 500 and "private" not in response.text


def test_openapi_file_matches_live_routes():
    path = Path(__file__).resolve().parents[1] / "openapi.yaml"
    assert yaml.safe_load(path.read_text(encoding="utf-8")) == app.openapi()
