"""Universal 12-Step License Validation Engine.

Executes a deterministic, multi-stage validation sequence for both online
and offline validation scenarios with structured status reporting.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from keyforge.core.crypto import (
    Ed25519KeyManager,
    KeyPair,
    verify_signature,
)
from keyforge.core.license_model import (
    LicensePayload,
    LicenseStatus,
    LicenseType,
    SignedLicense,
    ValidationResult,
    ValidationStatus,
)
from keyforge.core.profiles import ProductProfile


def _parse_iso_datetime(dt_str: str) -> datetime:
    """Parse ISO-8601 string to UTC datetime."""
    # Normalize 'Z' to '+00:00'
    clean = dt_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(clean)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _check_version_compatibility(
    client_version: str, allowed_versions: list[str]
) -> bool:
    """Evaluate whether client semver satisfies allowed_version constraints."""
    if not allowed_versions or "*" in allowed_versions or "all" in allowed_versions:
        return True

    # Simple matching supporting wildcards (e.g. "2.*", "2.1.*") and exact match
    for pattern in allowed_versions:
        if pattern == client_version:
            return True
        if pattern.endswith(".*"):
            prefix = pattern[:-2]
            if client_version.startswith(prefix):
                return True
        if pattern.startswith(">="):
            req = pattern[2:].strip()
            if client_version >= req:
                return True
        if pattern.startswith("<="):
            req = pattern[2:].strip()
            if client_version <= req:
                return True
    return False


class LicenseValidator:
    """Universal 12-step validation pipeline for online and offline licenses."""

    def __init__(
        self,
        public_key: KeyPair | str | bytes | None = None,
        key_manager: Ed25519KeyManager | None = None,
        profile: ProductProfile | None = None,
    ) -> None:
        self.public_key = public_key
        self.key_manager = key_manager
        self.profile = profile

    def validate_signed_license(
        self,
        license_input: SignedLicense | str | dict[str, Any],
        expected_product_id: str | None = None,
        client_version: str | None = None,
        device_id: str | None = None,
        required_feature: str | None = None,
        server_status: str | None = None,
        current_time: datetime | None = None,
    ) -> ValidationResult:
        """Run the comprehensive 12-step validation sequence.

        Args:
            license_input: SignedLicense instance, JSON string, compact token, or dict.
            expected_product_id: Product ID to enforce (optional).
            client_version: Software version running the check (optional).
            device_id: Installation/hardware ID (optional).
            required_feature: Specific feature to check entitlement for (optional).
            server_status: Known server-side status (e.g. from online API or local db).
            current_time: Reference time (defaults to current UTC).
        """
        now = current_time or datetime.now(timezone.utc)

        # Step 1: Parse and normalize input
        signed_lic: SignedLicense
        try:
            if isinstance(license_input, SignedLicense):
                signed_lic = license_input
            elif isinstance(license_input, str):
                s = license_input.strip()
                if s.startswith("kf1."):
                    signed_lic = SignedLicense.from_token(s)
                elif s.startswith("{"):
                    signed_lic = SignedLicense.from_json(s)
                else:
                    return ValidationResult(
                        is_valid=False,
                        status=ValidationStatus.INVALID_FORMAT,
                        message="Unsupported license format",
                    )
            elif isinstance(license_input, dict):
                signed_lic = SignedLicense.from_dict(license_input)
            else:
                return ValidationResult(
                    is_valid=False,
                    status=ValidationStatus.INVALID_FORMAT,
                    message="Invalid license object type",
                )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                status=ValidationStatus.INVALID_FORMAT,
                message=f"Failed to parse license: {str(e)}",
            )

        payload = signed_lic.payload

        # Step 2 & 3: Schema version verification
        if signed_lic.schema_version > 1 or payload.schema_version > 1:
            return ValidationResult(
                is_valid=False,
                status=ValidationStatus.LICENSE_SCHEMA_UNSUPPORTED,
                message=f"Unsupported license schema version: {payload.schema_version}",
                license_id=payload.license_id,
                product_id=payload.product_id,
            )

        # Step 4: Product ID validation
        target_product = (
            expected_product_id
            or (self.profile.product.id if self.profile else None)
        )
        if target_product and payload.product_id != target_product:
            return ValidationResult(
                is_valid=False,
                status=ValidationStatus.PRODUCT_MISMATCH,
                message=f"License is for product '{payload.product_id}', expected '{target_product}'",
                license_id=payload.license_id,
                product_id=payload.product_id,
            )

        # Step 5: Cryptographic signature verification
        pub_key = None
        if self.key_manager and signed_lic.key_id:
            keypair = self.key_manager.get_key(signed_lic.key_id)
            if keypair:
                pub_key = keypair
        if not pub_key:
            pub_key = self.public_key

        if not pub_key:
            return ValidationResult(
                is_valid=False,
                status=ValidationStatus.INVALID_SIGNATURE,
                message="No public verification key available to verify signature",
                license_id=payload.license_id,
                product_id=payload.product_id,
            )

        is_sig_valid = verify_signature(
            payload.to_dict(), signed_lic.signature, pub_key
        )
        if not is_sig_valid:
            return ValidationResult(
                is_valid=False,
                status=ValidationStatus.INVALID_SIGNATURE,
                message="Cryptographic signature verification failed (payload tampered or wrong key)",
                license_id=payload.license_id,
                product_id=payload.product_id,
            )

        # Step 6: Not-Before temporal check
        if payload.not_before:
            try:
                nb_dt = _parse_iso_datetime(payload.not_before)
                if now < nb_dt:
                    return ValidationResult(
                        is_valid=False,
                        status=ValidationStatus.NOT_YET_ACTIVE,
                        message=f"License is not active until {payload.not_before}",
                        license_id=payload.license_id,
                        product_id=payload.product_id,
                    )
            except Exception:
                pass

        # Step 7: Expiration temporal check
        days_remaining = None
        is_expired = False
        if payload.expires_at:
            try:
                exp_dt = _parse_iso_datetime(payload.expires_at)
                diff = exp_dt - now
                days_remaining = max(0, diff.days)
                if now > exp_dt:
                    is_expired = True
                    return ValidationResult(
                        is_valid=False,
                        status=ValidationStatus.EXPIRED,
                        message=f"License expired at {payload.expires_at}",
                        license_id=payload.license_id,
                        product_id=payload.product_id,
                        expires_at=payload.expires_at,
                        days_remaining=0,
                        is_expired=True,
                    )
            except Exception:
                pass

        # Step 8: Status validation (if known)
        effective_status = (server_status or "active").lower()
        if effective_status in ("revoked", LicenseStatus.REVOKED.value):
            return ValidationResult(
                is_valid=False,
                status=ValidationStatus.REVOKED,
                message="License has been revoked by the administrator",
                license_id=payload.license_id,
                product_id=payload.product_id,
            )
        if effective_status in ("suspended", LicenseStatus.SUSPENDED.value):
            return ValidationResult(
                is_valid=False,
                status=ValidationStatus.SUSPENDED,
                message="License is currently suspended",
                license_id=payload.license_id,
                product_id=payload.product_id,
            )

        # Step 9: Feature entitlement check
        if required_feature:
            has_feat = ("*" in payload.features) or (required_feature in payload.features)
            if not has_feat:
                return ValidationResult(
                    is_valid=False,
                    status=ValidationStatus.VALID,  # License itself is valid, but missing feature
                    message=f"Feature '{required_feature}' is not enabled in this license",
                    license_id=payload.license_id,
                    product_id=payload.product_id,
                    edition=payload.edition,
                    license_type=payload.license_type,
                    features=payload.features,
                    expires_at=payload.expires_at,
                    days_remaining=days_remaining,
                    customer_id=payload.customer_id,
                )

        # Step 10: Version policy compatibility check
        if client_version and payload.allowed_versions:
            if not _check_version_compatibility(client_version, payload.allowed_versions):
                return ValidationResult(
                    is_valid=False,
                    status=ValidationStatus.VERSION_NOT_SUPPORTED,
                    message=f"Client version '{client_version}' is not permitted by license policy ({payload.allowed_versions})",
                    license_id=payload.license_id,
                    product_id=payload.product_id,
                )

        # Step 11 & 12: Success packaging
        return ValidationResult(
            is_valid=True,
            status=ValidationStatus.VALID,
            message="License is valid and verified",
            license_id=payload.license_id,
            product_id=payload.product_id,
            edition=payload.edition,
            license_type=payload.license_type,
            features=payload.features,
            expires_at=payload.expires_at,
            days_remaining=days_remaining,
            is_expired=False,
            allowed_devices=payload.max_devices,
            customer_id=payload.customer_id,
            metadata=payload.metadata,
        )
