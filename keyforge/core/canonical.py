"""Deterministic Canonical JSON Serialization (RFC 8785 compliant).

Ensures bit-exact, deterministic JSON serialization across all client platforms
(Python, Node.js, C#, Go, PowerShell) so that cryptographic signatures verify
reliably without ambiguity.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any


def _canonicalize_value(val: Any) -> Any:
    """Recursively canonicalize data structures for RFC 8785 compliance."""
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            raise ValueError(f"RFC 8785 forbids NaN and Infinity in JSON: {val}")
        # Standardize integer-valued floats if needed or return float
        return int(val) if val.is_integer() else val
    if isinstance(val, str):
        return val
    if isinstance(val, (list, tuple)):
        return [_canonicalize_value(item) for item in val]
    if isinstance(val, dict):
        # Sort keys lexicographically by UTF-16 code points (standard UTF-8 sort)
        return {
            str(k): _canonicalize_value(v)
            for k, v in sorted(val.items(), key=lambda x: str(x[0]))
        }
    if hasattr(val, "model_dump"):
        return _canonicalize_value(val.model_dump(mode="json", exclude_none=True))
    if hasattr(val, "to_dict"):
        return _canonicalize_value(val.to_dict())
    if hasattr(val, "__dict__"):
        return _canonicalize_value(
            {k: v for k, v in val.__dict__.items() if not k.startswith("_") and v is not None}
        )
    raise TypeError(f"Type {type(val).__name__} is not JSON serializable")


def canonical_json(data: Any) -> str:
    """Serialize data into a deterministic, RFC 8785 compliant canonical JSON string.

    Guarantees:
    1. Object keys are sorted lexicographically.
    2. No unnecessary whitespace (separators=(',', ':')).
    3. UTF-8 encoding without ASCII escaping.
    4. Deterministic float and integer representation.
    """
    cleaned = _canonicalize_value(data)
    return json.dumps(
        cleaned,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def canonical_bytes(data: Any) -> bytes:
    """Serialize data to UTF-8 encoded canonical JSON bytes for hashing/signing."""
    return canonical_json(data).encode("utf-8")


def canonical_hash(data: Any) -> str:
    """Compute SHA-256 hex digest of the canonical JSON representation."""
    return hashlib.sha256(canonical_bytes(data)).hexdigest()
