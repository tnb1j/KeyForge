"""Asymmetric Cryptography Engine using Ed25519 (RFC 8032).

Provides cryptographically secure keypair generation, PEM/hex serialization,
deterministic signing over canonical payloads, multi-version key vault management,
and signature verification without exposing private keys to clients.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from keyforge.core.canonical import canonical_bytes


def b64url_encode(data: bytes) -> str:
    """Encode bytes into base64url string without padding."""
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def b64url_decode(s: str) -> bytes:
    """Decode base64url string with optional missing padding."""
    s_padded = s + "=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode(s_padded.encode("ascii"))


def secure_random_token(length_bytes: int = 16) -> str:
    """Generate a cryptographically secure hex token."""
    return secrets.token_hex(length_bytes)


def secure_random_id(prefix: str = "lic", length_bytes: int = 8) -> str:
    """Generate a secure identifier with a prefix, e.g. lic_a1b2c3d4e5f60718."""
    return f"{prefix}_{secrets.token_hex(length_bytes)}"


@dataclass
class KeyPair:
    """Represents an Ed25519 keypair and its cryptographic metadata."""

    key_id: str
    version: int
    algorithm: str = "Ed25519"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    public_key_pem: str = ""
    private_key_pem: str | None = None
    public_key_hex: str = ""
    fingerprint: str = ""
    status: str = "active"  # active, rotated, revoked

    def get_public_key_obj(self) -> ed25519.Ed25519PublicKey:
        """Load public key object from PEM or Hex."""
        if self.public_key_pem:
            return serialization.load_pem_public_key(
                self.public_key_pem.encode("utf-8")
            )  # type: ignore
        if self.public_key_hex:
            raw = bytes.fromhex(self.public_key_hex)
            return ed25519.Ed25519PublicKey.from_public_bytes(raw)
        raise ValueError("No public key material available")

    def get_private_key_obj(self) -> ed25519.Ed25519PrivateKey:
        """Load private key object from PEM."""
        if not self.private_key_pem:
            raise PermissionError("Private key material is not present (client-safe instance)")
        return serialization.load_pem_private_key(  # type: ignore
            self.private_key_pem.encode("utf-8"),
            password=None,
        )

    def to_public_dict(self) -> dict[str, Any]:
        """Return safe public-only metadata for client distribution or API responses."""
        return {
            "key_id": self.key_id,
            "version": self.version,
            "algorithm": self.algorithm,
            "status": self.status,
            "created_at": self.created_at,
            "public_key_pem": self.public_key_pem,
            "public_key_hex": self.public_key_hex,
            "fingerprint": self.fingerprint,
        }


def generate_keypair(version: int = 1, key_id: str | None = None) -> KeyPair:
    """Generate a new Ed25519 keypair with PEM serialization and SHA-256 fingerprint."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    raw_pub = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    pub_hex = raw_pub.hex()
    fingerprint = hashlib.sha256(raw_pub).hexdigest()

    if not key_id:
        key_id = f"key-v{version}-{pub_hex[:8]}"

    return KeyPair(
        key_id=key_id,
        version=version,
        algorithm="Ed25519",
        public_key_pem=pub_pem,
        private_key_pem=priv_pem,
        public_key_hex=pub_hex,
        fingerprint=fingerprint,
        status="active",
    )


def sign_payload(
    data: Any,
    private_key_input: ed25519.Ed25519PrivateKey | str | bytes | KeyPair,
) -> tuple[str, bytes]:
    """Sign canonicalized payload using Ed25519.

    Returns:
        tuple[str, bytes]: (signature_b64url, signature_raw_bytes)
    """
    if isinstance(private_key_input, KeyPair):
        priv_key = private_key_input.get_private_key_obj()
    elif isinstance(private_key_input, ed25519.Ed25519PrivateKey):
        priv_key = private_key_input
    elif isinstance(private_key_input, str):
        if "BEGIN PRIVATE KEY" in private_key_input:
            priv_key = serialization.load_pem_private_key(  # type: ignore
                private_key_input.encode("utf-8"),
                password=None,
            )
        else:
            # Assume hex encoded 32-byte seed
            raw_seed = bytes.fromhex(private_key_input.strip())
            priv_key = ed25519.Ed25519PrivateKey.from_private_bytes(raw_seed)
    elif isinstance(private_key_input, bytes):
        if b"BEGIN PRIVATE KEY" in private_key_input:
            priv_key = serialization.load_pem_private_key(  # type: ignore
                private_key_input,
                password=None,
            )
        else:
            priv_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_key_input)
    else:
        raise TypeError(f"Unsupported private key input type: {type(private_key_input)}")

    message_bytes = canonical_bytes(data)
    raw_sig = priv_key.sign(message_bytes)
    sig_b64 = b64url_encode(raw_sig)
    return sig_b64, raw_sig


def verify_signature(
    data: Any,
    signature_input: str | bytes,
    public_key_input: ed25519.Ed25519PublicKey | str | bytes | KeyPair,
) -> bool:
    """Verify an Ed25519 signature against canonicalized data.

    Returns:
        bool: True if signature is cryptographically authentic, False otherwise.
    """
    try:
        # Resolve public key
        if isinstance(public_key_input, KeyPair):
            pub_key = public_key_input.get_public_key_obj()
        elif isinstance(public_key_input, ed25519.Ed25519PublicKey):
            pub_key = public_key_input
        elif isinstance(public_key_input, str):
            if "BEGIN PUBLIC KEY" in public_key_input:
                pub_key = serialization.load_pem_public_key(  # type: ignore
                    public_key_input.encode("utf-8")
                )
            else:
                raw_pub = bytes.fromhex(public_key_input.strip())
                pub_key = ed25519.Ed25519PublicKey.from_public_bytes(raw_pub)
        elif isinstance(public_key_input, bytes):
            if b"BEGIN PUBLIC KEY" in public_key_input:
                pub_key = serialization.load_pem_public_key(public_key_input)  # type: ignore
            else:
                pub_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_input)
        else:
            return False

        # Resolve signature bytes
        if isinstance(signature_input, str):
            try:
                sig_bytes = b64url_decode(signature_input.strip())
            except Exception:
                # Try hex decode fallback
                sig_bytes = bytes.fromhex(signature_input.strip())
        elif isinstance(signature_input, bytes):
            sig_bytes = signature_input
        else:
            return False

        if len(sig_bytes) != 64:
            return False

        message_bytes = canonical_bytes(data)
        pub_key.verify(sig_bytes, message_bytes)
        return True
    except (InvalidSignature, ValueError, TypeError, Exception):
        return False


class Ed25519KeyManager:
    """Manages a collection of active and rotated signing keys with multi-version support."""

    def __init__(self) -> None:
        self._keys: dict[str, KeyPair] = {}
        self._active_key_id: str | None = None

    def add_key(self, keypair: KeyPair, set_active: bool = False) -> None:
        """Register a keypair in the vault."""
        self._keys[keypair.key_id] = keypair
        if set_active or self._active_key_id is None:
            self._active_key_id = keypair.key_id

    def get_key(self, key_id: str) -> KeyPair | None:
        """Get keypair by key ID."""
        return self._keys.get(key_id)

    def get_active_key(self) -> KeyPair | None:
        """Get the currently active signing key."""
        if not self._active_key_id:
            return None
        return self._keys.get(self._active_key_id)

    def get_by_version(self, version: int) -> KeyPair | None:
        """Find the latest active or rotated key matching the specified version."""
        candidates = [k for k in self._keys.values() if k.version == version]
        if not candidates:
            return None
        # Prefer active over rotated
        active = [k for k in candidates if k.status == "active"]
        return active[0] if active else candidates[0]

    def rotate_key(self, new_version: int | None = None) -> KeyPair:
        """Rotate to a newly generated keypair while maintaining historical keys for verification."""
        current_active = self.get_active_key()
        next_ver = (current_active.version + 1) if current_active else 1
        if new_version is not None:
            next_ver = new_version

        if current_active:
            current_active.status = "rotated"

        new_key = generate_keypair(version=next_ver)
        self.add_key(new_key, set_active=True)
        return new_key

    def export_public_vault(self) -> list[dict[str, Any]]:
        """Export client-safe public keys for verification trust stores."""
        return [k.to_public_dict() for k in self._keys.values() if k.status != "revoked"]
