"""KeyForge: Universal Adaptive Software Key & License Management Framework.

A production-grade, universal, configurable licensing and key-management platform
supporting online/offline validation, Ed25519 asymmetric cryptography, dynamic profiles,
and multi-language client SDKs.
"""

__version__ = "1.0.0"
__author__ = "KeyForge Architecture Team"

from keyforge.core.canonical import canonical_json, canonical_hash
from keyforge.core.crypto import (
    Ed25519KeyManager,
    generate_keypair,
    sign_payload,
    verify_signature,
)
from keyforge.core.key_generator import (
    KeyFormatConfig,
    generate_human_key,
    parse_and_validate_key,
)
from keyforge.core.license_model import (
    LicensePayload,
    LicenseStatus,
    LicenseType,
    SignedLicense,
    ValidationResult,
    ValidationStatus,
)
from keyforge.core.validator import LicenseValidator

__all__ = [
    "__version__",
    "canonical_json",
    "canonical_hash",
    "Ed25519KeyManager",
    "generate_keypair",
    "sign_payload",
    "verify_signature",
    "KeyFormatConfig",
    "generate_human_key",
    "parse_and_validate_key",
    "LicensePayload",
    "LicenseStatus",
    "LicenseType",
    "SignedLicense",
    "ValidationResult",
    "ValidationStatus",
    "LicenseValidator",
]
