"""Tests for Python SDK: KeyForgeClient, Storage Adapters, and ClockGuard."""

import pytest
import tempfile
from pathlib import Path
from keyforge.core.crypto import generate_keypair, sign_payload
from keyforge.core.license_model import LicensePayload, LicenseType, SignedLicense
from keyforge_client.client import KeyForgeClient
from keyforge_client.clock_guard import ClockGuard
from keyforge_client.storage import FileLicenseStorage, MemoryLicenseStorage


def test_python_sdk_memory_storage_offline_validation():
    kp = generate_keypair(version=1, key_id="key-v1-prod")
    payload = LicensePayload(
        license_id="lic_sdk_01",
        license_key="PROD-7K4M-9Q2X-8T6P",
        product_id="desktop-app",
        edition="pro",
        features=["ui", "export_pdf", "automation"],
        expires_at="2035-01-01T00:00:00Z",
    )
    sig_b64, _ = sign_payload(payload.to_dict(), kp)
    signed_lic = SignedLicense(
        schema_version=1,
        key_id=kp.key_id,
        algorithm="Ed25519",
        payload=payload,
        signature=sig_b64,
    )

    storage = MemoryLicenseStorage()
    storage.save_license(signed_lic.to_token())

    client = KeyForgeClient(
        product_id="desktop-app",
        public_key=kp,
        storage=storage,
    )

    assert client.is_valid() is True
    assert client.has_feature("export_pdf") is True
    assert client.has_feature("cloud_sync") is False
    assert client.get_edition() == "pro"


def test_python_sdk_clock_guard_tamper_detection():
    with tempfile.TemporaryDirectory() as tmpdir:
        guard_file = Path(tmpdir) / ".guard"
        guard = ClockGuard(state_file=guard_file)

        # Baseline timestamp update
        assert guard.check_and_update() is True

        # Now simulate clock rollback by checking with a past timestamp
        from datetime import datetime, timezone, timedelta
        past_time = datetime.now(timezone.utc) - timedelta(hours=2)
        assert guard.check_and_update(now=past_time) is False


def test_file_storage_integrity():
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "license.lic"
        storage = FileLicenseStorage(file_path=file_path)

        storage.save_license("kf1.dummy_payload.dummy_sig.dummy_key")
        loaded = storage.load_license()
        assert loaded == "kf1.dummy_payload.dummy_sig.dummy_key"

        # Tamper with file content directly
        raw_text = file_path.read_text()
        tampered_text = raw_text.replace("dummy_payload", "tampered_payload")
        file_path.write_text(tampered_text)

        # Loading should return None due to checksum mismatch
        assert storage.load_license() is None
