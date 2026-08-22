"""Integration tests for Authentication and API Key Endpoints."""

import pytest
from fastapi.testclient import TestClient
from keyforge.server.app import app
from keyforge.server.db.database import Base, engine, init_db


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db()


@pytest.fixture(scope="module")
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


def test_change_password(client):
    from keyforge.server.db.database import SessionLocal
    from keyforge.server.db.models import AdminUserModel
    from keyforge.server.auth import hash_password
    from keyforge.core.crypto import secure_random_id

    # Create dedicated test user
    db = SessionLocal()
    try:
        user_id = secure_random_id("usr", 8)
        u = AdminUserModel(
            id=user_id,
            username="pwd_test_user",
            password_hash=hash_password("OldPassword123!"),
            role="SUPER_ADMIN",
            is_active=True,
        )
        db.add(u)
        db.commit()
    finally:
        db.close()

    # 1. Login with initial password
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": "pwd_test_user", "password": "OldPassword123!"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    # 2. Change password
    change_res = client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "OldPassword123!",
            "new_password": "BrandNewPassword2026!",
        },
    )
    assert change_res.status_code == 200

    # 3. Login with new password
    new_login_res = client.post(
        "/api/v1/auth/login",
        json={"username": "pwd_test_user", "password": "BrandNewPassword2026!"},
    )
    assert new_login_res.status_code == 200
