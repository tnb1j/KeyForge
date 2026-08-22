"""Security and Negative Testing: Tampering, Forgery, Replay, and Bypass Defense."""

import pytest
from keyforge.core.crypto import generate_keypair, sign_payload, verify_signature
from keyforge.core.license_model import (
    LicensePayload,
    LicenseType,
    SignedLicense,
    ValidationStatus,
)
from keyforge.core.validator import LicenseValidator


def test_tampered_payload_edition_elevation():
    """Verify that altering edition claim invalidates Ed25519 signature."""
    kp = generate_keypair(version=1)
    payload = LicensePayload(
        license_id="lic_tamper_1",
        product_id="my_app",
        edition="starter",
        features=["basic"],
    )
    sig_b64, _ = sign_payload(payload.to_dict(), kp)

    # Attacker tries to change edition to 'enterprise' in the payload
    tampered_payload = LicensePayload(
        license_id="lic_tamper_1",
        product_id="my_app",
        edition="enterprise",
        features=["basic", "export", "admin"],
    )
    signed_lic = SignedLicense(
        schema_version=1,
        key_id=kp.key_id,
        algorithm="Ed25519",
        payload=tampered_payload,
        signature=sig_b64,
    )

    validator = LicenseValidator(public_key=kp)
    res = validator.validate_signed_license(signed_lic, expected_product_id="my_app")
    assert res.is_valid is False
    assert res.status == ValidationStatus.INVALID_SIGNATURE


def test_tampered_expiration_extension():
    """Verify that tampering with expires_at timestamp fails signature check."""
    kp = generate_keypair(version=1)
    payload = LicensePayload(
        license_id="lic_tamper_2",
        product_id="my_app",
        expires_at="2020-01-01T00:00:00Z",
    )
    sig_b64, _ = sign_payload(payload.to_dict(), kp)

    # Attacker alters expires_at to year 2099
    tampered_payload = LicensePayload(
        license_id="lic_tamper_2",
        product_id="my_app",
        expires_at="2099-12-31T23:59:59Z",
    )
    signed_lic = SignedLicense(
        schema_version=1,
        key_id=kp.key_id,
        algorithm="Ed25519",
        payload=tampered_payload,
        signature=sig_b64,
    )

    validator = LicenseValidator(public_key=kp)
    res = validator.validate_signed_license(signed_lic, expected_product_id="my_app")
    assert res.is_valid is False
    assert res.status == ValidationStatus.INVALID_SIGNATURE


def test_cross_product_substitution_attack():
    """Verify that a valid license for Product A is strictly rejected by Product B."""
    kp = generate_keypair(version=1)
    payload = LicensePayload(
        license_id="lic_app_a",
        product_id="product-alpha",
        edition="enterprise",
    )
    sig_b64, _ = sign_payload(payload.to_dict(), kp)
    signed_lic = SignedLicense(
        schema_version=1,
        key_id=kp.key_id,
        algorithm="Ed25519",
        payload=payload,
        signature=sig_b64,
    )

    validator = LicenseValidator(public_key=kp)
    # Target application expects 'product-beta'
    res = validator.validate_signed_license(
        signed_lic, expected_product_id="product-beta"
    )
    assert res.is_valid is False
    assert res.status == ValidationStatus.PRODUCT_MISMATCH


def test_corrupted_signature_bytes():
    """Verify that malformed or bit-flipped signatures fail safely."""
    kp = generate_keypair(version=1)
    payload = LicensePayload(license_id="lic_corrupt", product_id="my_app")
    sig_b64, _ = sign_payload(payload.to_dict(), kp)

    # Bit-flip signature string
    corrupted_sig = ("A" if sig_b64[0] != "A" else "B") + sig_b64[1:]
    signed_lic = SignedLicense(
        schema_version=1,
        key_id=kp.key_id,
        algorithm="Ed25519",
        payload=payload,
        signature=corrupted_sig,
    )

    validator = LicenseValidator(public_key=kp)
    res = validator.validate_signed_license(signed_lic, expected_product_id="my_app")
    assert res.is_valid is False
    assert res.status == ValidationStatus.INVALID_SIGNATURE
