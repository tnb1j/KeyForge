"""Unit tests for Ed25519 Cryptography and Key Management."""

import pytest
from keyforge.core.crypto import (
    Ed25519KeyManager,
    KeyPair,
    b64url_decode,
    b64url_encode,
    generate_keypair,
    secure_random_id,
    secure_random_token,
    sign_payload,
    verify_signature,
)


def test_keypair_generation():
    kp = generate_keypair(version=1, key_id="key-test-1")
    assert kp.algorithm == "Ed25519"
    assert kp.version == 1
    assert kp.key_id == "key-test-1"
    assert "BEGIN PUBLIC KEY" in kp.public_key_pem
    assert kp.private_key_pem is not None
    assert "BEGIN PRIVATE KEY" in kp.private_key_pem
    assert len(kp.public_key_hex) == 64
    assert len(kp.fingerprint) == 64


def test_sign_and_verify_valid_payload():
    kp = generate_keypair(version=1)
    payload = {
        "license_id": "lic_123",
        "product_id": "demo_app",
        "customer": "alice@example.com",
    }
    sig_b64, raw_sig = sign_payload(payload, kp)
    assert isinstance(sig_b64, str)
    assert len(raw_sig) == 64

    # Verify with KeyPair instance
    assert verify_signature(payload, sig_b64, kp) is True
    # Verify with PEM public key string
    assert verify_signature(payload, sig_b64, kp.public_key_pem) is True
    # Verify with Hex public key string
    assert verify_signature(payload, sig_b64, kp.public_key_hex) is True


def test_tampered_payload_fails_verification():
    kp = generate_keypair(version=1)
    original_payload = {"license_id": "lic_123", "features": ["basic"]}
    sig_b64, _ = sign_payload(original_payload, kp)

    # Modify feature entitlement
    tampered_payload = {"license_id": "lic_123", "features": ["basic", "enterprise"]}
    assert verify_signature(tampered_payload, sig_b64, kp) is False


def test_wrong_key_fails_verification():
    kp1 = generate_keypair(version=1)
    kp2 = generate_keypair(version=1)
    payload = {"license_id": "lic_123"}

    sig_b64, _ = sign_payload(payload, kp1)
    # Attempt verification against kp2 public key
    assert verify_signature(payload, sig_b64, kp2) is False


def test_key_vault_rotation():
    manager = Ed25519KeyManager()
    k1 = generate_keypair(version=1)
    manager.add_key(k1, set_active=True)
    assert manager.get_active_key().key_id == k1.key_id

    k2 = manager.rotate_key(new_version=2)
    assert manager.get_active_key().key_id == k2.key_id
    assert manager.get_key(k1.key_id).status == "rotated"
    assert manager.get_key(k2.key_id).status == "active"

    # Both keys can still be looked up
    assert manager.get_by_version(1).key_id == k1.key_id
    assert manager.get_by_version(2).key_id == k2.key_id


def test_secure_random_generators():
    id1 = secure_random_id("lic", 8)
    id2 = secure_random_id("lic", 8)
    assert id1.startswith("lic_")
    assert id1 != id2
    assert len(secure_random_token(16)) == 32
