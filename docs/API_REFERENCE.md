# KeyForge REST API Reference

The KeyForge API conforms to REST principles and OpenAPI 3.1 specifications. Interactive Swagger UI is accessible at `/docs` and ReDoc at `/redoc`.

## Base URL
```text
http://127.0.0.1:8000/api/v1
```

---

## 1. Authentication Endpoints

### `POST /auth/login`
Authenticate administrator credentials and receive a JWT Bearer token.
* **Request**:
```json
{
  "username": "admin",
  "password": "KeyForgeAdmin2026!"
}
```
* **Response (200 OK)**:
```json
{
  "access_token": "eyJhbGciOiAiSFMyNTYi...",
  "token_type": "Bearer",
  "expires_in_minutes": 1440,
  "user": {
    "id": "usr_a1b2c3d4",
    "username": "admin",
    "role": "SUPER_ADMIN"
  }
}
```

---

## 2. License Endpoints

### `POST /licenses`
Issue a new cryptographically signed software license.
* **Headers**: `Authorization: Bearer <token>`
* **Request**:
```json
{
  "product_id": "desktop-app",
  "customer_id": "cust_1001",
  "customer_email": "alice@example.com",
  "license_type": "subscription",
  "edition": "pro",
  "features": ["ui", "export_pdf", "cloud_sync"],
  "max_devices": 3,
  "duration_days": 365
}
```
* **Response (201 Created)**:
```json
{
  "id": "lic_8f29d12a",
  "license_key": "DSK-7K4M-9Q2X-8T6P",
  "product_id": "desktop-app",
  "customer_id": "cust_1001",
  "edition": "pro",
  "status": "active",
  "expires_at": "2027-08-22T00:00:00Z",
  "features": ["ui", "export_pdf", "cloud_sync"],
  "max_devices": 3,
  "signed_token": "kf1.eyJjdXN0b21lci...3da3a8c6"
}
```

### `POST /licenses/activate`
Activate a software installation on a client machine.
* **Request**:
```json
{
  "license_key": "DSK-7K4M-9Q2X-8T6P",
  "product_id": "desktop-app",
  "installation_id": "inst_7781a9",
  "device_fingerprint": "fp_hash_device_01",
  "device_name": "Workstation 1",
  "platform": "windows",
  "client_version": "1.0.0"
}
```
* **Response (200 OK)**:
```json
{
  "success": true,
  "message": "Device activated successfully",
  "license": { ... },
  "activation": {
    "activation_id": "act_8829a1",
    "installation_id": "inst_7781a9",
    "activated_at": "2026-08-22T00:00:00Z",
    "signature": "..."
  }
}
```

### `POST /licenses/validate`
Online license validation and heartbeat ping.
* **Request**:
```json
{
  "license_key": "DSK-7K4M-9Q2X-8T6P",
  "product_id": "desktop-app",
  "installation_id": "inst_7781a9",
  "client_version": "1.0.0"
}
```
* **Response (200 OK)**:
```json
{
  "is_valid": true,
  "status": "VALID",
  "message": "License is active and valid",
  "license_id": "lic_8f29d12a",
  "edition": "pro",
  "features": ["ui", "export_pdf", "cloud_sync"],
  "days_remaining": 364,
  "allowed_devices": 3,
  "active_devices": 1
}
```
