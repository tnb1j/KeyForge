"""Universal Product Configuration and Profile Engine.

Defines product-level licensing policies, key formats, activation rules,
feature maps, and profile presets without hard-coding application-specific logic.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from keyforge.core.key_generator import (
    AlphabetType,
    ChecksumType,
    KeyFormatConfig,
)


@dataclass
class ProductInfo:
    id: str = "default-product"
    name: str = "Default Product"
    version: str = "1.0.0"
    description: str = ""


@dataclass
class ActivationPolicy:
    enabled: bool = True
    max_devices_default: int = 3
    require_online_activation: bool = False
    heartbeat_interval_seconds: int = 86400  # 24 hours
    offline_grace_period_days: int = 7


@dataclass
class ExpirationPolicy:
    allow_lifetime: bool = True
    default_subscription_days: int = 365
    default_trial_days: int = 14


@dataclass
class FeaturesPolicy:
    available_features: list[str] = field(
        default_factory=lambda: ["core", "export", "automation", "api"]
    )
    default_features: list[str] = field(default_factory=lambda: ["core"])
    editions: dict[str, list[str]] = field(
        default_factory=lambda: {
            "community": ["core"],
            "professional": ["core", "export", "automation"],
            "enterprise": ["*"],
        }
    )


@dataclass
class SecurityPolicy:
    signature_algorithm: str = "Ed25519"
    min_key_version: int = 1
    allow_offline_validation: bool = True
    enable_clock_guard: bool = True


@dataclass
class ProductProfile:
    """Master configuration profile for a product's licensing system."""

    product: ProductInfo = field(default_factory=ProductInfo)
    key_format: KeyFormatConfig = field(default_factory=KeyFormatConfig)
    activation: ActivationPolicy = field(default_factory=ActivationPolicy)
    expiration: ExpirationPolicy = field(default_factory=ExpirationPolicy)
    features: FeaturesPolicy = field(default_factory=FeaturesPolicy)
    security: SecurityPolicy = field(default_factory=SecurityPolicy)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "product": asdict(self.product),
            "key_format": self.key_format.to_dict(),
            "activation": asdict(self.activation),
            "expiration": asdict(self.expiration),
            "features": asdict(self.features),
            "security": asdict(self.security),
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProductProfile:
        prod_data = data.get("product", {})
        product = ProductInfo(
            id=str(prod_data.get("id", "default-product")),
            name=str(prod_data.get("name", "Default Product")),
            version=str(prod_data.get("version", "1.0.0")),
            description=str(prod_data.get("description", "")),
        )

        kf_data = data.get("key_format", {})
        key_format = KeyFormatConfig.from_dict(kf_data) if kf_data else KeyFormatConfig()

        act_data = data.get("activation", {})
        activation = ActivationPolicy(
            enabled=bool(act_data.get("enabled", True)),
            max_devices_default=int(act_data.get("max_devices_default", 3)),
            require_online_activation=bool(act_data.get("require_online_activation", False)),
            heartbeat_interval_seconds=int(act_data.get("heartbeat_interval_seconds", 86400)),
            offline_grace_period_days=int(act_data.get("offline_grace_period_days", 7)),
        )

        exp_data = data.get("expiration", {})
        expiration = ExpirationPolicy(
            allow_lifetime=bool(exp_data.get("allow_lifetime", True)),
            default_subscription_days=int(exp_data.get("default_subscription_days", 365)),
            default_trial_days=int(exp_data.get("default_trial_days", 14)),
        )

        feat_data = data.get("features", {})
        features = FeaturesPolicy(
            available_features=list(feat_data.get("available_features", ["core", "export"])),
            default_features=list(feat_data.get("default_features", ["core"])),
            editions=dict(
                feat_data.get(
                    "editions",
                    {
                        "community": ["core"],
                        "professional": ["core", "export"],
                        "enterprise": ["*"],
                    },
                )
            ),
        )

        sec_data = data.get("security", {})
        security = SecurityPolicy(
            signature_algorithm=str(sec_data.get("signature_algorithm", "Ed25519")),
            min_key_version=int(sec_data.get("min_key_version", 1)),
            allow_offline_validation=bool(sec_data.get("allow_offline_validation", True)),
            enable_clock_guard=bool(sec_data.get("enable_clock_guard", True)),
        )

        return cls(
            product=product,
            key_format=key_format,
            activation=activation,
            expiration=expiration,
            features=features,
            security=security,
            metadata=dict(data.get("metadata", {})),
        )


def get_default_profile(profile_type: str = "desktop") -> ProductProfile:
    """Factory for standard product profile templates."""
    if profile_type == "desktop":
        return ProductProfile(
            product=ProductInfo(id="desktop-app", name="Desktop Application", version="1.0.0"),
            key_format=KeyFormatConfig(
                prefix="DSK",
                raw_length=16,
                group_size=4,
                separator="-",
                alphabet_type=AlphabetType.CROCKFORD_BASE32,
                checksum_type=ChecksumType.LUHN_MOD32,
            ),
            activation=ActivationPolicy(
                enabled=True,
                max_devices_default=3,
                require_online_activation=False,
                offline_grace_period_days=14,
            ),
            features=FeaturesPolicy(
                available_features=["ui", "export_pdf", "batch_processing", "cloud_sync"],
                default_features=["ui"],
                editions={
                    "standard": ["ui", "export_pdf"],
                    "pro": ["ui", "export_pdf", "batch_processing", "cloud_sync"],
                },
            ),
        )

    elif profile_type == "saas_api":
        return ProductProfile(
            product=ProductInfo(id="saas-service", name="Cloud SaaS API", version="2.0.0"),
            key_format=KeyFormatConfig(
                prefix="API",
                raw_length=20,
                group_size=5,
                separator="-",
                alphabet_type=AlphabetType.ALPHANUMERIC_NO_AMBIGUOUS,
                checksum_type=ChecksumType.CRC8,
            ),
            activation=ActivationPolicy(
                enabled=True,
                max_devices_default=10,
                require_online_activation=True,
                heartbeat_interval_seconds=3600,
            ),
            features=FeaturesPolicy(
                available_features=["read", "write", "admin", "webhooks", "unlimited_rate"],
                default_features=["read"],
                editions={
                    "developer": ["read", "write"],
                    "enterprise": ["*"],
                },
            ),
        )

    elif profile_type == "air_gapped":
        return ProductProfile(
            product=ProductInfo(
                id="secure-enterprise", name="Air-Gapped Enterprise Suite", version="3.0.0"
            ),
            key_format=KeyFormatConfig(
                prefix="SEC",
                raw_length=24,
                group_size=6,
                separator="-",
                alphabet_type=AlphabetType.CROCKFORD_BASE32,
                checksum_type=ChecksumType.LUHN_MOD32,
            ),
            activation=ActivationPolicy(
                enabled=False,
                max_devices_default=1,
                require_online_activation=False,
                offline_grace_period_days=365,
            ),
            security=SecurityPolicy(
                allow_offline_validation=True,
                enable_clock_guard=True,
            ),
        )

    return ProductProfile()
