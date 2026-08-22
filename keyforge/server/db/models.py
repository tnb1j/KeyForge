"""SQLAlchemy Database Schema for KeyForge Licensing Engine."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProductModel(Base):
    """Registered products with active configuration profiles."""

    __tablename__ = "products"

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    version = Column(String(32), nullable=False, default="1.0.0")
    description = Column(Text, nullable=True)
    profile_json = Column(Text, nullable=False)  # ProductProfile JSON serialization
    active_key_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    licenses = relationship("LicenseModel", back_populates="product", cascade="all, delete-orphan")
    keys = relationship("SigningKeyModel", back_populates="product", cascade="all, delete-orphan")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "profile": json.loads(self.profile_json) if self.profile_json else {},
            "active_key_id": self.active_key_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SigningKeyModel(Base):
    """Cryptographic signing keypairs registered for products."""

    __tablename__ = "signing_keys"

    key_id = Column(String(64), primary_key=True)
    product_id = Column(String(64), ForeignKey("products.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    algorithm = Column(String(32), nullable=False, default="Ed25519")
    public_key_pem = Column(Text, nullable=False)
    public_key_hex = Column(String(64), nullable=False)
    private_key_pem = Column(Text, nullable=False)  # Protected server-side only
    fingerprint = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default="active")  # active, rotated, revoked
    created_at = Column(DateTime, default=utc_now, nullable=False)
    expires_at = Column(DateTime, nullable=True)

    product = relationship("ProductModel", back_populates="keys")

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "key_id": self.key_id,
            "product_id": self.product_id,
            "version": self.version,
            "algorithm": self.algorithm,
            "public_key_pem": self.public_key_pem,
            "public_key_hex": self.public_key_hex,
            "fingerprint": self.fingerprint,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class LicenseModel(Base):
    """Issued licenses and their authorization metadata."""

    __tablename__ = "licenses"

    id = Column(String(64), primary_key=True)  # e.g. lic_8f29d12a
    license_key_raw = Column(String(128), unique=True, nullable=False, index=True)
    license_key_masked = Column(String(128), nullable=False)
    product_id = Column(String(64), ForeignKey("products.id"), nullable=False, index=True)
    customer_id = Column(String(128), nullable=False, index=True)
    customer_email = Column(String(256), nullable=True, index=True)
    license_type = Column(String(32), nullable=False, default="subscription")
    edition = Column(String(64), nullable=False, default="standard")
    status = Column(String(32), nullable=False, default="active", index=True)
    issued_at = Column(DateTime, default=utc_now, nullable=False)
    not_before = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    features_json = Column(Text, nullable=False, default="[]")
    max_devices = Column(Integer, nullable=False, default=1)
    max_activations = Column(Integer, nullable=False, default=1)
    allowed_versions_json = Column(Text, nullable=False, default='["*"]')
    metadata_json = Column(Text, nullable=False, default="{}")
    key_id = Column(String(64), nullable=False)
    key_version = Column(Integer, nullable=False, default=1)
    signature = Column(Text, nullable=False)
    signed_token = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    product = relationship("ProductModel", back_populates="licenses")
    activations = relationship("ActivationModel", back_populates="license", cascade="all, delete-orphan")

    def to_dict(self, include_token: bool = True) -> dict[str, Any]:
        d = {
            "id": self.id,
            "license_key": self.license_key_raw,
            "license_key_masked": self.license_key_masked,
            "product_id": self.product_id,
            "customer_id": self.customer_id,
            "customer_email": self.customer_email,
            "license_type": self.license_type,
            "edition": self.edition,
            "status": self.status,
            "issued_at": self.issued_at.isoformat() if self.issued_at else None,
            "not_before": self.not_before.isoformat() if self.not_before else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "features": json.loads(self.features_json) if self.features_json else [],
            "max_devices": self.max_devices,
            "max_activations": self.max_activations,
            "active_devices_count": len([a for a in self.activations if a.status == "active"]) if self.activations else 0,
            "allowed_versions": json.loads(self.allowed_versions_json) if self.allowed_versions_json else ["*"],
            "metadata": json.loads(self.metadata_json) if self.metadata_json else {},
            "key_id": self.key_id,
            "key_version": self.key_version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_token:
            d["signature"] = self.signature
            d["signed_token"] = self.signed_token
        return d


class ActivationModel(Base):
    """Device/installation activation bindings."""

    __tablename__ = "activations"

    id = Column(String(64), primary_key=True)  # act_xxx
    license_id = Column(String(64), ForeignKey("licenses.id"), nullable=False, index=True)
    installation_id = Column(String(128), nullable=False, index=True)
    device_fingerprint = Column(String(128), nullable=False)
    device_name = Column(String(128), nullable=True)
    platform = Column(String(64), nullable=True)
    client_version = Column(String(32), nullable=True)
    ip_address_masked = Column(String(64), nullable=True)
    status = Column(String(32), nullable=False, default="active")  # active, deactivated, revoked
    activated_at = Column(DateTime, default=utc_now, nullable=False)
    last_heartbeat_at = Column(DateTime, default=utc_now, nullable=False)
    metadata_json = Column(Text, nullable=False, default="{}")

    license = relationship("LicenseModel", back_populates="activations")

    __table_args__ = (
        UniqueConstraint("license_id", "installation_id", name="uq_license_installation"),
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "license_id": self.license_id,
            "installation_id": self.installation_id,
            "device_fingerprint": self.device_fingerprint,
            "device_name": self.device_name,
            "platform": self.platform,
            "client_version": self.client_version,
            "ip_address_masked": self.ip_address_masked,
            "status": self.status,
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
            "last_heartbeat_at": self.last_heartbeat_at.isoformat() if self.last_heartbeat_at else None,
            "metadata": json.loads(self.metadata_json) if self.metadata_json else {},
        }


class AuditEventModel(Base):
    """Structured security audit records."""

    __tablename__ = "audit_events"

    id = Column(String(64), primary_key=True)
    event_type = Column(String(64), nullable=False, index=True)
    actor_id = Column(String(128), nullable=False)
    actor_type = Column(String(32), nullable=False, default="admin")  # admin, client, system
    license_id = Column(String(64), nullable=True, index=True)
    product_id = Column(String(64), nullable=True, index=True)
    ip_address = Column(String(64), nullable=True)
    timestamp = Column(DateTime, default=utc_now, nullable=False, index=True)
    reason = Column(String(256), nullable=True)
    details_json = Column(Text, nullable=False, default="{}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "license_id": self.license_id,
            "product_id": self.product_id,
            "ip_address": self.ip_address,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "reason": self.reason,
            "details": json.loads(self.details_json) if self.details_json else {},
        }


class AdminUserModel(Base):
    """Administrator accounts and API integration keys."""

    __tablename__ = "admin_users"

    id = Column(String(64), primary_key=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    role = Column(String(32), nullable=False, default="SUPER_ADMIN")
    api_key_hash = Column(String(64), unique=True, nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    last_login_at = Column(DateTime, nullable=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }
