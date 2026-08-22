"""Integration tests for Authentication and API Key Endpoints."""

import pytest
from fastapi.testclient import TestClient
from keyforge.server.app import app
from keyforge.server.db.database import Base, engine, init_db


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db()


@pytest.fixture
def client():
    return TestClient(app)


def test_login_successful(client):
    res = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "KeyForgeAdmin2026!"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "Bearer"
    assert data["user"]["username"] == "admin"


def test_login_invalid_password(client):
    res = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "WrongPassword!"},
    )
    assert res.status_code == 401


def test_get_me_with_jwt(client):
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "KeyForgeAdmin2026!"},
    )
    token = login_res.json()["access_token"]

    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "admin"
