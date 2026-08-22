"""Unit tests for the Universal 12-Step License Validation Engine."""

from datetime import datetime, timezone, timedelta
import pytest
from keyforge.core.crypto import generate_keypair, sign_payload
from keyforge.core.license_model import (
    LicensePayload,
    LicenseStatus,
    LicenseType,
    SignedLicense,
    ValidationStatus,
)
from keyforge.core.validator import LicenseValidator


def test_validation_valid_signed_license(master_keypair):
    validator = LicenseValidator(public_key=master_keypair)
    payload = LicensePayload(
        license_id="lic_001",
        product_id="my_app",
        edition="pro",
        customer_id="alice",
        features=["advanced"],
        expires_at="2035-01-01T00:00:00Z",
    )
    sig_b64, _ = sign_payload(payload.to_dict(), master_keypair)
    signed_lic = SignedLicense(
        schema_version=1,
        key_id=master_keypair.key_id,
        algorithm="Ed25519",
        payload=payload,
        signature=sig_b64,
    )

    res = validator.validate_signed_license(
        signed_lic, expected_product_id="my_app", required_feature="advanced"
    )
    assert res.is_valid is True
    assert res.status == ValidationStatus.VALID
    assert res.edition == "pro"
    assert res.has_feature("advanced") is True


def test_validation_expired_license(master_keypair):
    validator = LicenseValidator(public_key=master_keypair)
    past_date = "2020-01-01T00:00:00Z"
    payload = LicensePayload(
        license_id="lic_expired",
        product_id="my_app",
        expires_at=past_date,
    )
    sig_b64, _ = sign_payload(payload.to_dict(), master_keypair)
    signed_lic = SignedLicense(
        schema_version=1,
        key_id=master_keypair.key_id,
        algorithm="Ed25519",
        payload=payload,
        signature=sig_b64,
    )

    res = validator.validate_signed_license(signed_lic, expected_product_id="my_app")
    assert res.is_valid is False
    assert res.status == ValidationStatus.EXPIRED
    assert res.is_expired is True


def test_validation_future_not_before(master_keypair):
    validator = LicenseValidator(public_key=master_keypair)
    future_date = "2099-01-01T00:00:00Z"
    payload = LicensePayload(
        license_id="lic_future",
        product_id="my_app",
        not_before=future_date,
    )
    sig_b64, _ = sign_payload(payload.to_dict(), master_keypair)
    signed_lic = SignedLicense(
        schema_version=1,
        key_id=master_keypair.key_id,
        algorithm="Ed25519",
        payload=payload,
        signature=sig_b64,
    )

    res = validator.validate_signed_license(signed_lic, expected_product_id="my_app")
    assert res.is_valid is False
    assert res.status == ValidationStatus.NOT_YET_ACTIVE


def test_validation_product_mismatch(master_keypair):
    validator = LicenseValidator(public_key=master_keypair)
    payload = LicensePayload(
        license_id="lic_002",
        product_id="other_app",
    )
    sig_b64, _ = sign_payload(payload.to_dict(), master_keypair)
    signed_lic = SignedLicense(
        schema_version=1,
        key_id=master_keypair.key_id,
        algorithm="Ed25519",
        payload=payload,
        signature=sig_b64,
    )

    res = validator.validate_signed_license(signed_lic, expected_product_id="target_app")
    assert res.is_valid is False
    assert res.status == ValidationStatus.PRODUCT_MISMATCH


def test_validation_revoked_status(master_keypair):
    validator = LicenseValidator(public_key=master_keypair)
    payload = LicensePayload(
        license_id="lic_revoked",
        product_id="my_app",
    )
    sig_b64, _ = sign_payload(payload.to_dict(), master_keypair)
    signed_lic = SignedLicense(
        schema_version=1,
        key_id=master_keypair.key_id,
        algorithm="Ed25519",
        payload=payload,
        signature=sig_b64,
    )

    res = validator.validate_signed_license(
        signed_lic, expected_product_id="my_app", server_status="revoked"
    )
    assert res.is_valid is False
    assert res.status == ValidationStatus.REVOKED


def test_validation_version_policy(master_keypair):
    validator = LicenseValidator(public_key=master_keypair)
    payload = LicensePayload(
        license_id="lic_ver",
        product_id="my_app",
        allowed_versions=[">=2.0.0"],
    )
    sig_b64, _ = sign_payload(payload.to_dict(), master_keypair)
    signed_lic = SignedLicense(
        schema_version=1,
        key_id=master_keypair.key_id,
        algorithm="Ed25519",
        payload=payload,
        signature=sig_b64,
    )

    # 1.5.0 should fail
    res_bad = validator.validate_signed_license(
        signed_lic, expected_product_id="my_app", client_version="1.5.0"
    )
    assert res_bad.is_valid is False
    assert res_bad.status == ValidationStatus.VERSION_NOT_SUPPORTED

    # 2.2.0 should pass
    res_good = validator.validate_signed_license(
        signed_lic, expected_product_id="my_app", client_version="2.2.0"
    )
    assert res_good.is_valid is True
    assert res_good.status == ValidationStatus.VALID
