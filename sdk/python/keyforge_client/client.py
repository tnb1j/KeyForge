"""KeyForge Universal Python Client SDK.

Provides high-level license initialization, online activation, offline Ed25519
signature verification, feature entitlement queries, anti-clock-rollback tracking,
and secure local persistence.
"""

from __future__ import annotations

import json
from typing import Any, Optional
import httpx

from keyforge.core.crypto import KeyPair, verify_signature
from keyforge.core.license_model import (
    LicensePayload,
    LicenseStatus,
    SignedLicense,
    ValidationResult,
    ValidationStatus,
)
from keyforge.core.validator import LicenseValidator
from keyforge_client.clock_guard import ClockGuard
from keyforge_client.device import get_device_fingerprint, get_installation_id
from keyforge_client.storage import BaseLicenseStorage, FileLicenseStorage, WindowsDPAPILicenseStorage


class KeyForgeClient:
    """Universal software licensing client for Python desktop, CLI, and backend applications."""

    def __init__(
        self,
        product_id: str,
        public_key: KeyPair | str | bytes | None = None,
        server_url: Optional[str] = None,
        client_version: str = "1.0.0",
        storage: Optional[BaseLicenseStorage] = None,
        enable_clock_guard: bool = True,
    ) -> None:
        self.product_id = product_id
        self.public_key = public_key
        self.server_url = server_url.rstrip("/") if server_url else None
        self.client_version = client_version
        self.storage = storage or FileLicenseStorage()
        self.clock_guard = ClockGuard() if enable_clock_guard else None
        self.validator = LicenseValidator(public_key=self.public_key)
        self.cached_license: Optional[SignedLicense] = None
        self.last_validation_result: Optional[ValidationResult] = None

        # Load persisted license if available
        self._load_stored_license()

    def _load_stored_license(self) -> None:
        stored = self.storage.load_license()
        if stored:
            try:
                if stored.startswith("kf1."):
                    self.cached_license = SignedLicense.from_token(stored)
                elif stored.startswith("{"):
                    self.cached_license = SignedLicense.from_json(stored)
            except Exception:
                self.cached_license = None

    def is_valid(self) -> bool:
        """Check if the currently active license is valid."""
        if not self.last_validation_result:
            self.validate()
        return self.last_validation_result.is_valid if self.last_validation_result else False

    def has_feature(self, feature_name: str) -> bool:
        """Check if the current license entitles the user to a specific feature."""
        if not self.last_validation_result:
            self.validate()
        if not self.last_validation_result or not self.last_validation_result.is_valid:
            return False
        return self.last_validation_result.has_feature(feature_name)

    def get_days_remaining(self) -> Optional[int]:
        """Return number of days until license expiration, or None if lifetime."""
        if not self.last_validation_result:
            self.validate()
        return self.last_validation_result.days_remaining if self.last_validation_result else None

    def get_edition(self) -> str:
        """Get current license edition (e.g. 'standard', 'pro', 'enterprise')."""
        if self.cached_license:
            return self.cached_license.payload.edition
        return "unlicensed"

    def validate(
        self, license_input: SignedLicense | str | None = None
    ) -> ValidationResult:
        """Validate license either offline using public key or online with server."""
        # Check clock rollback
        if self.clock_guard and not self.clock_guard.check_and_update():
            res = ValidationResult(
                is_valid=False,
                status=ValidationStatus.CLOCK_ROLLBACK_DETECTED,
                message="System clock rollback detected. Validation denied.",
                product_id=self.product_id,
            )
            self.last_validation_result = res
            return res

        target_lic = license_input or self.cached_license
        if not target_lic:
            res = ValidationResult(
                is_valid=False,
                status=ValidationStatus.UNKNOWN_LICENSE,
                message="No license loaded or provided",
                product_id=self.product_id,
            )
            self.last_validation_result = res
            return res

        # Run offline validation first if public verification key is present
        if self.public_key:
            res = self.validator.validate_signed_license(
                target_lic,
                expected_product_id=self.product_id,
                client_version=self.client_version,
            )
            self.last_validation_result = res
            return res

        # Fallback to online validation if server URL provided
        if self.server_url:
            return self._validate_online(target_lic)

        res = ValidationResult(
            is_valid=False,
            status=ValidationStatus.INVALID_SIGNATURE,
            message="Cannot validate license: neither public key nor server URL configured",
            product_id=self.product_id,
        )
        self.last_validation_result = res
        return res

    def _validate_online(self, license_obj: SignedLicense | str) -> ValidationResult:
        key_str = (
            license_obj.payload.license_key
            if isinstance(license_obj, SignedLicense)
            else str(license_obj)
        )
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(
                    f"{self.server_url}/api/v1/licenses/validate",
                    json={
                        "license_key": key_str,
                        "product_id": self.product_id,
                        "installation_id": get_installation_id(),
                        "client_version": self.client_version,
                    },
                )
                if res.status_code == 200:
                    data = res.json()
                    val_res = ValidationResult(
                        is_valid=data["is_valid"],
                        status=ValidationStatus(data["status"]),
                        message=data["message"],
                        license_id=data.get("license_id"),
                        product_id=data.get("product_id"),
                        edition=data.get("edition"),
                        features=data.get("features", []),
                        expires_at=data.get("expires_at"),
                        days_remaining=data.get("days_remaining"),
                        is_expired=data.get("is_expired", False),
                        allowed_devices=data.get("allowed_devices", 1),
                        active_devices=data.get("active_devices", 0),
                        customer_id=data.get("customer_id"),
                    )
                    self.last_validation_result = val_res
                    return val_res
        except Exception as e:
            pass

        # Offline fallback error
        res = ValidationResult(
            is_valid=False,
            status=ValidationStatus.SERVER_UNAVAILABLE,
            message="Server unavailable for online validation and no offline key present",
            product_id=self.product_id,
        )
        self.last_validation_result = res
        return res

    def activate(
        self,
        license_key: str,
        device_name: Optional[str] = None,
        platform_name: Optional[str] = None,
    ) -> dict[str, Any]:
        """Perform online device activation and store the resulting license locally."""
        if not self.server_url:
            raise ValueError("Online activation requires 'server_url' parameter")

        installation_id = get_installation_id()
        device_fp = get_device_fingerprint()

        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                f"{self.server_url}/api/v1/licenses/activate",
                json={
                    "license_key": license_key.strip(),
                    "product_id": self.product_id,
                    "installation_id": installation_id,
                    "device_fingerprint": device_fp,
                    "device_name": device_name or "Desktop Station",
                    "platform": platform_name or "windows",
                    "client_version": self.client_version,
                },
            )
            if resp.status_code != 200:
                detail = resp.json().get("detail", f"Activation failed ({resp.status_code})")
                raise RuntimeError(detail)

            data = resp.json()
            lic_dict = data.get("license", {})
            token = lic_dict.get("signed_token")
            if token:
                self.cached_license = SignedLicense.from_token(token)
                self.storage.save_license(token)

            self.validate()
            return data

    def deactivate(self) -> dict[str, Any]:
        """Deactivate this installation from the licensing server and clear local license."""
        if not self.server_url or not self.cached_license:
            self.storage.clear_license()
            self.cached_license = None
            return {"success": True, "message": "Local license cleared"}

        key_str = self.cached_license.payload.license_key
        try:
            with httpx.Client(timeout=10.0) as client:
                client.post(
                    f"{self.server_url}/api/v1/licenses/deactivate",
                    json={
                        "license_key": key_str,
                        "installation_id": get_installation_id(),
                    },
                )
        except Exception:
            pass

        self.storage.clear_license()
        self.cached_license = None
        self.last_validation_result = None
        return {"success": True, "message": "Installation deactivated"}
