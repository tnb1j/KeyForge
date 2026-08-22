"""Integration tests for License Lifecycle API (Issuance, Batch, Renew, Revoke, Export)."""

import pytest
from fastapi.testclient import TestClient
from keyforge.server.app import app
from keyforge.server.db.database import init_db


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db()


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def admin_token(client):
    res = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "KeyForgeAdmin2026!"},
    )
    return res.json()["access_token"]


def test_issue_single_license(client, admin_token):
    res = client.post(
        "/api/v1/licenses",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "product_id": "desktop-app",
            "customer_id": "cust_john_doe",
            "customer_email": "john@example.com",
            "license_type": "subscription",
            "edition": "pro",
            "duration_days": 30,
            "features": ["ui", "export_pdf", "cloud_sync"],
            "max_devices": 3,
        },
    )
    assert res.status_code == 201
    lic = res.json()
    assert lic["product_id"] == "desktop-app"
    assert lic["customer_id"] == "cust_john_doe"
    assert lic["status"] == "active"
    assert lic["max_devices"] == 3
    assert "signed_token" in lic
    assert lic["signed_token"].startswith("kf1.")
    assert "signature" in lic


def test_batch_issue_licenses(client, admin_token):
    res = client.post(
        "/api/v1/licenses/batch",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "product_id": "desktop-app",
            "quantity": 25,
            "customer_id_prefix": "bulk_client",
            "edition": "standard",
            "duration_days": 90,
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["quantity"] == 25
    assert len(data["licenses"]) >= 20


def test_license_lifecycle_suspend_reactivate_renew_revoke(client, admin_token):
    # Issue license
    res = client.post(
        "/api/v1/licenses",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "product_id": "desktop-app",
            "customer_id": "cust_lifecycle",
            "duration_days": 10,
        },
    )
    lic_id = res.json()["id"]

    # Suspend
    sus_res = client.post(
        f"/api/v1/licenses/{lic_id}/suspend",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"reason": "Payment investigation"},
    )
    assert sus_res.status_code == 200
    assert sus_res.json()["status"] == "suspended"

    # Reactivate
    react_res = client.post(
        f"/api/v1/licenses/{lic_id}/reactivate",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"reason": "Payment cleared"},
    )
    assert react_res.status_code == 200
    assert react_res.json()["status"] == "active"

    # Renew
    renew_res = client.post(
        f"/api/v1/licenses/{lic_id}/renew",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"extend_days": 365, "reason": "Customer renewed 1 year"},
    )
    assert renew_res.status_code == 200
    assert renew_res.json()["status"] == "active"

    # Export .lic file
    exp_res = client.get(
        f"/api/v1/licenses/{lic_id}/export?format=lic_file",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert exp_res.status_code == 200
    assert "filename" in exp_res.json()
    assert "content" in exp_res.json()

    # Revoke
    rev_res = client.post(
        f"/api/v1/licenses/{lic_id}/revoke",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"reason": "Chargeback dispute"},
    )
    assert rev_res.status_code == 200
    assert rev_res.json()["status"] == "revoked"


def test_delete_license(client, admin_token):
    # Issue a disposable license
    issue_res = client.post(
        "/api/v1/licenses",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "product_id": "desktop-app",
            "customer_id": "cust_disposable",
            "duration_days": 10,
        },
    )
    lic_id = issue_res.json()["id"]

    # Delete it
    del_res = client.delete(
        f"/api/v1/licenses/{lic_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert del_res.status_code == 200
    assert del_res.json()["deleted_id"] == lic_id

    # Verify 404 on get
    get_res = client.get(
        f"/api/v1/licenses/{lic_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_res.status_code == 404


def test_purge_all_licenses(client, admin_token):
    # Issue multiple test licenses
    for i in range(3):
        client.post(
            "/api/v1/licenses",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "product_id": "desktop-app",
                "customer_id": f"cust_purge_{i}",
                "duration_days": 10,
            },
        )

    # Purge all
    purge_res = client.post(
        "/api/v1/licenses/purge-all",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert purge_res.status_code == 200
    assert "deleted_licenses" in purge_res.json()

    # List licenses should be empty
    list_res = client.get(
        "/api/v1/licenses",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 0
