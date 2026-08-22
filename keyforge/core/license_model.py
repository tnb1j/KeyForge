"""License Domain Object Model and Schema Definitions.

Defines immutable, strongly-typed representations of License Claims, Signed License
Tokens, Activation Receipts, and Validation Statuses.
"""

from __future__ import annotations

import enum
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from keyforge.core.canonical import canonical_json
from keyforge.core.crypto import b64url_decode, b64url_encode


class LicenseType(str, enum.Enum):
    TRIAL = "trial"
    LIFETIME = "lifetime"
    SUBSCRIPTION = "subscription"
    FEATURE = "feature"
    DEVICE_BOUND = "device_bound"
    USER_BOUND = "user_bound"
    ORGANIZATION_BOUND = "organization_bound"
    HYBRID = "hybrid"
    ENTERPRISE = "enterprise"


class LicenseStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    EXPIRED = "expired"
    DEACTIVATED = "deactivated"
    TRANSFERRED = "transferred"


class ValidationStatus(str, enum.Enum):
    VALID = "VALID"
    INVALID_FORMAT = "INVALID_FORMAT"
    INVALID_SIGNATURE = "INVALID_SIGNATURE"
    UNKNOWN_LICENSE = "UNKNOWN_LICENSE"
    NOT_YET_ACTIVE = "NOT_YET_ACTIVE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    SUSPENDED = "SUSPENDED"
    ACTIVATION_LIMIT_REACHED = "ACTIVATION_LIMIT_REACHED"
    DEVICE_NOT_AUTHORIZED = "DEVICE_NOT_AUTHORIZED"
    PRODUCT_MISMATCH = "PRODUCT_MISMATCH"
    VERSION_NOT_SUPPORTED = "VERSION_NOT_SUPPORTED"
    LICENSE_SCHEMA_UNSUPPORTED = "LICENSE_SCHEMA_UNSUPPORTED"
    OFFLINE_GRACE_EXPIRED = "OFFLINE_GRACE_EXPIRED"
    CLOCK_ROLLBACK_DETECTED = "CLOCK_ROLLBACK_DETECTED"
    SERVER_UNAVAILABLE = "SERVER_UNAVAILABLE"


@dataclass
class LicensePayload:
    """Core cryptographic claims payload signed by the licensing authority."""

    schema_version: int = 1
    license_id: str = ""
    license_key: str = ""
    product_id: str = ""
    license_type: LicenseType = LicenseType.SUBSCRIPTION
    edition: str = "standard"
    customer_id: str = ""
    customer_email: str | None = None
    issued_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    not_before: str | None = None
    expires_at: str | None = None  # None indicates Lifetime
    features: list[str] = field(default_factory=list)
    max_devices: int = 1
    max_activations: int = 1
    allowed_versions: list[str] = field(default_factory=lambda: ["*"])
    metadata: dict[str, Any] = field(default_factory=dict)
    key_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Convert payload to serializable dictionary."""
        d = asdict(self)
        if isinstance(d["license_type"], LicenseType):
            d["license_type"] = d["license_type"].value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LicensePayload:
        """Instantiate LicensePayload from a dictionary with type safety."""
        ltype = data.get("license_type", LicenseType.SUBSCRIPTION.value)
        if isinstance(ltype, str):
            try:
                ltype = LicenseType(ltype.lower())
            except ValueError:
                ltype = LicenseType.SUBSCRIPTION

        return cls(
            schema_version=int(data.get("schema_version", 1)),
            license_id=str(data.get("license_id", "")),
            license_key=str(data.get("license_key", "")),
            product_id=str(data.get("product_id", "")),
            license_type=ltype,
            edition=str(data.get("edition", "standard")),
            customer_id=str(data.get("customer_id", "")),
            customer_email=data.get("customer_email"),
            issued_at=str(data.get("issued_at", datetime.now(timezone.utc).isoformat())),
            not_before=data.get("not_before"),
            expires_at=data.get("expires_at"),
            features=list(data.get("features", [])),
            max_devices=int(data.get("max_devices", 1)),
            max_activations=int(data.get("max_activations", 1)),
            allowed_versions=list(data.get("allowed_versions", ["*"])),
            metadata=dict(data.get("metadata", {})),
            key_version=int(data.get("key_version", 1)),
        )


@dataclass
class SignedLicense:
    """Envelope containing license claims and cryptographic Ed25519 signature."""

    schema_version: int
    key_id: str
    algorithm: str
    payload: LicensePayload
    signature: str  # Base64URL encoded 64-byte Ed25519 signature

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "key_id": self.key_id,
            "algorithm": self.algorithm,
            "payload": self.payload.to_dict(),
            "signature": self.signature,
        }

    def to_json(self, indent: int | None = 2) -> str:
        """Export as pretty or compact JSON."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_token(self) -> str:
        """Export as compact armored token: kf1.<b64url_payload>.<b64url_sig>.<b64url_key_id>."""
        payload_canon = canonical_json(self.payload.to_dict())
        payload_b64 = b64url_encode(payload_canon.encode("utf-8"))
        key_id_b64 = b64url_encode(self.key_id.encode("utf-8"))
        return f"kf1.{payload_b64}.{self.signature}.{key_id_b64}"

    @classmethod
    def from_token(cls, token: str) -> SignedLicense:
        """Parse compact armored token representation."""
        parts = token.strip().split(".")
        if len(parts) != 4 or parts[0] != "kf1":
            raise ValueError("Invalid KeyForge armored token format")

        payload_bytes = b64url_decode(parts[1])
        payload_dict = json.loads(payload_bytes.decode("utf-8"))
        signature = parts[2]
        key_id = b64url_decode(parts[3]).decode("utf-8")

        payload = LicensePayload.from_dict(payload_dict)
        return cls(
            schema_version=1,
            key_id=key_id,
            algorithm="Ed25519",
            payload=payload,
            signature=signature,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SignedLicense:
        return cls(
            schema_version=int(data.get("schema_version", 1)),
            key_id=str(data.get("key_id", "")),
            algorithm=str(data.get("algorithm", "Ed25519")),
            payload=LicensePayload.from_dict(data["payload"]),
            signature=str(data.get("signature", "")),
        )

    @classmethod
    def from_json(cls, json_str: str) -> SignedLicense:
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class ActivationReceipt:
    """Cryptographic activation proof issued to a specific client installation."""

    activation_id: str
    license_id: str
    product_id: str
    installation_id: str
    device_fingerprint: str
    activated_at: str
    expires_at: str | None
    heartbeat_interval_seconds: int = 86400  # 24 hours
    key_id: str = ""
    signature: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ActivationReceipt:
        return cls(
            activation_id=str(data.get("activation_id", "")),
            license_id=str(data.get("license_id", "")),
            product_id=str(data.get("product_id", "")),
            installation_id=str(data.get("installation_id", "")),
            device_fingerprint=str(data.get("device_fingerprint", "")),
            activated_at=str(data.get("activated_at", "")),
            expires_at=data.get("expires_at"),
            heartbeat_interval_seconds=int(data.get("heartbeat_interval_seconds", 86400)),
            key_id=str(data.get("key_id", "")),
            signature=str(data.get("signature", "")),
        )


@dataclass
class ActivationRecord:
    """Internal server record of an active device."""

    id: str
    license_id: str
    installation_id: str
    device_fingerprint: str
    device_name: str | None
    platform: str | None
    client_version: str | None
    ip_address_masked: str | None
    status: str
    activated_at: str
    last_heartbeat_at: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Detailed evaluation result returned by the validation engine."""

    is_valid: bool
    status: ValidationStatus
    message: str
    license_id: str | None = None
    product_id: str | None = None
    edition: str | None = None
    license_type: LicenseType | None = None
    features: list[str] = field(default_factory=list)
    expires_at: str | None = None
    days_remaining: int | None = None
    is_expired: bool = False
    allowed_devices: int = 1
    active_devices: int = 0
    customer_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def has_feature(self, feature_name: str) -> bool:
        """Convenience query for feature entitlement."""
        if not self.is_valid:
            return False
        return ("*" in self.features) or (feature_name in self.features)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "status": self.status.value,
            "message": self.message,
            "license_id": self.license_id,
            "product_id": self.product_id,
            "edition": self.edition,
            "license_type": self.license_type.value if self.license_type else None,
            "features": self.features,
            "expires_at": self.expires_at,
            "days_remaining": self.days_remaining,
            "is_expired": self.is_expired,
            "allowed_devices": self.allowed_devices,
            "active_devices": self.active_devices,
            "customer_id": self.customer_id,
            "metadata": self.metadata,
        }
