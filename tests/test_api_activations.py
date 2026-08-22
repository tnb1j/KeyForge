"""Integration tests for Activation, Seat Limits, and Online Validation."""

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


def test_activation_seat_limit_and_deactivation(client, admin_token):
    # Issue license with max_devices = 2
    res = client.post(
        "/api/v1/licenses",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "product_id": "desktop-app",
            "customer_id": "cust_device_test",
            "max_devices": 2,
            "duration_days": 30,
        },
    )
    assert res.status_code == 201
    lic_key = res.json()["license_key"]
    lic_id = res.json()["id"]

    # Activate Device 1
    act1 = client.post(
        "/api/v1/licenses/activate",
        json={
            "license_key": lic_key,
            "product_id": "desktop-app",
            "installation_id": "inst-win-01",
            "device_fingerprint": "fp_hash_device_01",
            "device_name": "Alice Laptop",
            "platform": "windows",
        },
    )
    assert act1.status_code == 200
    assert act1.json()["success"] is True
    assert "activation" in act1.json()

    # Activate Device 2
    act2 = client.post(
        "/api/v1/licenses/activate",
        json={
            "license_key": lic_key,
            "product_id": "desktop-app",
            "installation_id": "inst-win-02",
            "device_fingerprint": "fp_hash_device_02",
            "device_name": "Alice Workstation",
            "platform": "windows",
        },
    )
    assert act2.status_code == 200
    assert act2.json()["success"] is True

    # Attempt to activate Device 3 (Should fail with 409 Conflict - seat limit)
    act3 = client.post(
        "/api/v1/licenses/activate",
        json={
            "license_key": lic_key,
            "product_id": "desktop-app",
            "installation_id": "inst-win-03",
            "device_fingerprint": "fp_hash_device_03",
            "device_name": "Alice Server",
            "platform": "windows",
        },
    )
    assert act3.status_code == 409
    assert "seat limit reached" in act3.json()["detail"].lower()

    # Online validate device 1
    val_res = client.post(
        "/api/v1/licenses/validate",
        json={
            "license_key": lic_key,
            "product_id": "desktop-app",
            "installation_id": "inst-win-01",
        },
    )
    assert val_res.status_code == 200
    assert val_res.json()["is_valid"] is True
    assert val_res.json()["active_devices"] == 2

    # Deactivate Device 1
    deact_res = client.post(
        "/api/v1/licenses/deactivate",
        json={"license_key": lic_key, "installation_id": "inst-win-01"},
    )
    assert deact_res.status_code == 200

    # Now Device 3 should succeed
    act3_retry = client.post(
        "/api/v1/licenses/activate",
        json={
            "license_key": lic_key,
            "product_id": "desktop-app",
            "installation_id": "inst-win-03",
            "device_fingerprint": "fp_hash_device_03",
            "device_name": "Alice Server",
            "platform": "windows",
        },
    )
    assert act3_retry.status_code == 200
    assert act3_retry.json()["success"] is True
