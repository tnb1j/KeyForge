"""Integration tests for Product Management and Key Vault Endpoints."""

import pytest
from fastapi.testclient import TestClient
from keyforge.server.app import app
from keyforge.server.db.database import init_db


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def admin_token(client):
    res = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "KeyForgeAdmin2026!"},
    )
    return res.json()["access_token"]


def test_list_products(client, admin_token):
    res = client.get("/api/v1/products", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    prods = res.json()
    assert isinstance(prods, list)
    assert any(p["id"] == "desktop-app" for p in prods)


import uuid

def test_create_and_get_custom_product(client, admin_token):
    prod_id = f"test-saas-{uuid.uuid4().hex[:6]}"
    res = client.post(
        "/api/v1/products",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "id": prod_id,
            "name": "Test SaaS Product",
            "version": "2.1.0",
            "profile_preset": "saas_api",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["id"] == prod_id
    assert data["active_key_id"] is not None

    # Get product
    get_res = client.get(
        f"/api/v1/products/{prod_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Test SaaS Product"


def test_rotate_product_key(client, admin_token):
    res = client.post(
        "/api/v1/keys/desktop-app/rotate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "new_key" in data
    assert data["new_key"]["version"] >= 2
