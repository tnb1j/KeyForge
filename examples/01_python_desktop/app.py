"""Example 1: Python Desktop / CLI Application with KeyForge Licensing.

Demonstrates:
- Offline Ed25519 signature verification with bundled public key.
- Feature gating based on license claims.
- Graceful unlicensed / trial state handling.
"""

import sys
from pathlib import Path

# Add project roots to sys.path for demo purposes
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "sdk" / "python"))

from keyforge.core.crypto import generate_keypair, sign_payload
from keyforge.core.license_model import LicensePayload, LicenseType, SignedLicense
from keyforge_client.client import KeyForgeClient
from keyforge_client.storage import MemoryLicenseStorage


def simulate_app_run():
    print("=" * 60)
    print("    PhotoStudio Pro - Desktop Image Processing Suite")
    print("=" * 60)

    # 1. Generate demo issuer keypair and sample signed license
    issuer_keys = generate_keypair(version=1, key_id="key-v1-photostudio")
    sample_payload = LicensePayload(
        schema_version=1,
        license_id="lic_photo_882",
        license_key="PHOTO-7K4M-9Q2X-8T6P",
        product_id="photostudio",
        license_type=LicenseType.SUBSCRIPTION,
        edition="professional",
        customer_id="alice@creative.io",
        features=["ui", "raw_export", "batch_filter", "cloud_backup"],
        expires_at="2030-01-01T00:00:00Z",
    )
    sig_b64, _ = sign_payload(sample_payload.to_dict(), issuer_keys)
    signed_license = SignedLicense(
        schema_version=1,
        key_id=issuer_keys.key_id,
        algorithm="Ed25519",
        payload=sample_payload,
        signature=sig_b64,
    )

    # 2. Store license in client storage
    storage = MemoryLicenseStorage()
    storage.save_license(signed_license.to_token())

    # 3. Initialize Client SDK with Public Verification Key (Private key is NEVER in client!)
    client = KeyForgeClient(
        product_id="photostudio",
        public_key=issuer_keys.public_key_pem,
        storage=storage,
        client_version="2.4.0",
    )

    # 4. Check license validity
    if not client.is_valid():
        print("[!] Software is UNLICENSED. Please enter a valid license key.")
        return

    print(f"[OK] License Status: VALID")
    print(f"    Edition:        {client.get_edition().upper()}")
    print(f"    Days Left:      {client.get_days_remaining()} days")

    # 5. Feature Entitlement Gates
    print("\n--- Feature Gate Check ---")
    features_to_test = ["raw_export", "batch_filter", "ai_super_resolution", "cloud_backup"]
    for feat in features_to_test:
        enabled = client.has_feature(feat)
        status = "[ENABLED] " if enabled else "[LOCKED]  "
        print(f"  {status} Feature '{feat}'")

    print("\n[+] Application successfully initialized with offline Ed25519 validation!")


if __name__ == "__main__":
    simulate_app_run()
