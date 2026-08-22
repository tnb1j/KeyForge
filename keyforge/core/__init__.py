"""KeyForge Core Module.

Contains cryptographic primitives, canonical serialization, key generation,
data models, configuration profiles, and the universal validation engine.
"""

from keyforge.core.canonical import canonical_hash, canonical_json
from keyforge.core.crypto import (
    Ed25519KeyManager,
    KeyPair,
    generate_keypair,
    sign_payload,
    verify_signature,
)
from keyforge.core.key_generator import (
    AlphabetType,
    ChecksumType,
    KeyFormatConfig,
    generate_human_key,
    parse_and_validate_key,
)
from keyforge.core.license_model import (
    ActivationReceipt,
    ActivationRecord,
    LicensePayload,
    LicenseStatus,
    LicenseType,
    SignedLicense,
    ValidationResult,
    ValidationStatus,
)
from keyforge.core.profiles import ProductProfile, get_default_profile
from keyforge.core.validator import LicenseValidator

__all__ = [
    "canonical_json",
    "canonical_hash",
    "KeyPair",
    "Ed25519KeyManager",
    "generate_keypair",
    "sign_payload",
    "verify_signature",
    "AlphabetType",
    "ChecksumType",
    "KeyFormatConfig",
    "generate_human_key",
    "parse_and_validate_key",
    "LicensePayload",
    "SignedLicense",
    "ActivationRecord",
    "ActivationReceipt",
    "LicenseStatus",
    "LicenseType",
    "ValidationStatus",
    "ValidationResult",
    "ProductProfile",
    "get_default_profile",
    "LicenseValidator",
]
