"""Unit tests for License Domain Model and Tokenization."""

import pytest
from keyforge.core.crypto import generate_keypair, sign_payload
from keyforge.core.license_model import (
    LicensePayload,
    LicenseStatus,
    LicenseType,
    SignedLicense,
    ValidationResult,
    ValidationStatus,
)


def test_license_payload_serialization():
    payload = LicensePayload(
        license_id="lic_abc123",
        license_key="PROD-1234-5678",
        product_id="desktop_app",
        license_type=LicenseType.SUBSCRIPTION,
        edition="pro",
        customer_id="cust_456",
        features=["export", "automation"],
        max_devices=3,
        expires_at="2030-01-01T00:00:00Z",
    )
    d = payload.to_dict()
    assert d["license_id"] == "lic_abc123"
    assert d["license_type"] == "subscription"
    assert d["max_devices"] == 3

    # Roundtrip from dict
    reloaded = LicensePayload.from_dict(d)
    assert reloaded.license_id == payload.license_id
    assert reloaded.license_type == LicenseType.SUBSCRIPTION
    assert reloaded.features == ["export", "automation"]


def test_signed_license_armored_token_roundtrip():
    kp = generate_keypair(version=1, key_id="key-v1-prod")
    payload = LicensePayload(
        license_id="lic_999",
        product_id="my_tool",
        customer_id="user@example.com",
        features=["core", "premium"],
        expires_at="2030-12-31T23:59:59Z",
    )
    sig_b64, _ = sign_payload(payload.to_dict(), kp)

    signed_lic = SignedLicense(
        schema_version=1,
        key_id=kp.key_id,
        algorithm="Ed25519",
        payload=payload,
        signature=sig_b64,
    )

    token = signed_lic.to_token()
    assert token.startswith("kf1.")

    parsed_lic = SignedLicense.from_token(token)
    assert parsed_lic.key_id == kp.key_id
    assert parsed_lic.payload.license_id == "lic_999"
    assert parsed_lic.payload.features == ["core", "premium"]
    assert parsed_lic.signature == sig_b64


def test_validation_result_feature_check():
    res = ValidationResult(
        is_valid=True,
        status=ValidationStatus.VALID,
        message="Valid",
        features=["export", "analytics"],
    )
    assert res.has_feature("export") is True
    assert res.has_feature("analytics") is True
    assert res.has_feature("admin") is False

    # Wildcard feature grant
    res_wildcard = ValidationResult(
        is_valid=True,
        status=ValidationStatus.VALID,
        message="Valid",
        features=["*"],
    )
    assert res_wildcard.has_feature("anything") is True
