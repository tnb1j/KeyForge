"""Human-Readable License Key Generator and Formatter.

Generates customizable, error-resistant license keys with optical normalization
and error-detecting checksums (e.g., Crockford Base32 with Luhn mod-32).
"""

from __future__ import annotations

import enum
import secrets
from dataclasses import dataclass
from typing import ClassVar


class AlphabetType(str, enum.Enum):
    CROCKFORD_BASE32 = "CROCKFORD_BASE32"
    ALPHANUMERIC_NO_AMBIGUOUS = "ALPHANUMERIC_NO_AMBIGUOUS"
    HEXADECIMAL = "HEXADECIMAL"
    ALPHANUMERIC_STANDARD = "ALPHANUMERIC_STANDARD"
    CUSTOM = "CUSTOM"


class ChecksumType(str, enum.Enum):
    LUHN_MOD32 = "LUHN_MOD32"
    CRC8 = "CRC8"
    NONE = "NONE"


ALPHABETS = {
    AlphabetType.CROCKFORD_BASE32: "0123456789ABCDEFGHJKMNPQRSTVWXYZ",
    AlphabetType.ALPHANUMERIC_NO_AMBIGUOUS: "23456789ABCDEFGHJKLMNPQRSTUVWXYZ",
    AlphabetType.HEXADECIMAL: "0123456789ABCDEF",
    AlphabetType.ALPHANUMERIC_STANDARD: "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ",
}

# Normalization map for common optical/typo confusions
CROCKFORD_NORMALIZATION = {
    "i": "1",
    "I": "1",
    "l": "1",
    "L": "1",
    "o": "0",
    "O": "0",
    "u": "V",  # Crockford spec maps U to V to avoid profanity
    "U": "V",
}


def _compute_luhn_mod32_check_char(payload: str, alphabet: str) -> str:
    """Compute Crockford Luhn-mod-32 check character."""
    n = len(alphabet)
    total = 0
    for i, ch in enumerate(reversed(payload)):
        val = alphabet.index(ch)
        weight = 2 if (i % 2 == 0) else 1
        product = val * weight
        total += (product // n) + (product % n)
    remainder = total % n
    check_val = (n - remainder) % n
    return alphabet[check_val]


def _compute_crc8(data: bytes) -> int:
    """Compute 8-bit CRC (polynomial 0x07)."""
    crc = 0x00
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x07) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc


@dataclass
class KeyFormatConfig:
    """Configuration for formatting human-readable license keys."""

    prefix: str = ""
    suffix: str = ""
    raw_length: int = 16
    group_size: int = 4
    separator: str = "-"
    alphabet_type: AlphabetType = AlphabetType.CROCKFORD_BASE32
    custom_alphabet: str | None = None
    checksum_type: ChecksumType = ChecksumType.LUHN_MOD32
    case_sensitive: bool = False

    def get_alphabet(self) -> str:
        """Resolve the effective character alphabet."""
        if self.alphabet_type == AlphabetType.CUSTOM:
            if not self.custom_alphabet or len(self.custom_alphabet) < 2:
                raise ValueError("Custom alphabet must contain at least 2 distinct characters")
            return self.custom_alphabet
        return ALPHABETS[self.alphabet_type]

    def to_dict(self) -> dict:
        return {
            "prefix": self.prefix,
            "suffix": self.suffix,
            "raw_length": self.raw_length,
            "group_size": self.group_size,
            "separator": self.separator,
            "alphabet_type": self.alphabet_type.value,
            "custom_alphabet": self.custom_alphabet,
            "checksum_type": self.checksum_type.value,
            "case_sensitive": self.case_sensitive,
        }

    @classmethod
    def from_dict(cls, data: dict) -> KeyFormatConfig:
        return cls(
            prefix=data.get("prefix", ""),
            suffix=data.get("suffix", ""),
            raw_length=int(data.get("raw_length", 16)),
            group_size=int(data.get("group_size", 4)),
            separator=data.get("separator", "-"),
            alphabet_type=AlphabetType(data.get("alphabet_type", AlphabetType.CROCKFORD_BASE32.value)),
            custom_alphabet=data.get("custom_alphabet"),
            checksum_type=ChecksumType(data.get("checksum_type", ChecksumType.LUHN_MOD32.value)),
            case_sensitive=bool(data.get("case_sensitive", False)),
        )


def generate_human_key(config: KeyFormatConfig | None = None) -> str:
    """Generate a formatted, cryptographically random, human-readable license key."""
    if config is None:
        config = KeyFormatConfig()

    alphabet = config.get_alphabet()
    alphabet_len = len(alphabet)

    payload_len = config.raw_length
    if config.checksum_type != ChecksumType.NONE:
        # Reserve 1 character for check digit
        payload_len = max(1, config.raw_length - 1)

    # Generate CSPRNG characters
    raw_chars = [secrets.choice(alphabet) for _ in range(payload_len)]
    payload_str = "".join(raw_chars)

    # Append Checksum if enabled
    if config.checksum_type == ChecksumType.LUHN_MOD32:
        check_char = _compute_luhn_mod32_check_char(payload_str, alphabet)
        full_raw = payload_str + check_char
    elif config.checksum_type == ChecksumType.CRC8:
        crc = _compute_crc8(payload_str.encode("utf-8"))
        check_char = alphabet[crc % alphabet_len]
        full_raw = payload_str + check_char
    else:
        full_raw = payload_str

    # Apply grouping
    if config.group_size > 0:
        chunks = [
            full_raw[i : i + config.group_size]
            for i in range(0, len(full_raw), config.group_size)
        ]
        formatted_body = config.separator.join(chunks)
    else:
        formatted_body = full_raw

    # Assemble prefix and suffix
    parts = []
    if config.prefix:
        parts.append(config.prefix.rstrip(config.separator))
    parts.append(formatted_body)
    if config.suffix:
        parts.append(config.suffix.lstrip(config.separator))

    return config.separator.join(p for p in parts if p)


def normalize_key_input(raw_input: str, config: KeyFormatConfig | None = None) -> str:
    """Normalize raw user input by stripping separators and replacing common optical typos."""
    if config is None:
        config = KeyFormatConfig()

    s = raw_input.strip()
    if not config.case_sensitive:
        s = s.upper()

    # Strip custom prefix/suffix if present
    if config.prefix:
        p_clean = config.prefix.strip(config.separator)
        if not config.case_sensitive:
            p_clean = p_clean.upper()
        if s.startswith(p_clean):
            s = s[len(p_clean) :].lstrip(config.separator)

    if config.suffix:
        s_clean = config.suffix.strip(config.separator)
        if not config.case_sensitive:
            s_clean = s_clean.upper()
        if s.endswith(s_clean):
            s = s[: -len(s_clean)].rstrip(config.separator)

    # Remove all separators and whitespace
    for sep in [config.separator, "-", "_", " ", "\t", "\n"]:
        s = s.replace(sep, "")

    # Apply Crockford typo corrections if using Crockford Base32
    if config.alphabet_type == AlphabetType.CROCKFORD_BASE32:
        normalized_chars = [CROCKFORD_NORMALIZATION.get(c, c) for c in s]
        s = "".join(normalized_chars)

    return s


def parse_and_validate_key(
    key_input: str, config: KeyFormatConfig | None = None
) -> tuple[bool, str, str]:
    """Validate a formatted license key.

    Returns:
        tuple[bool, str, str]: (is_valid, normalized_raw_key, error_message)
    """
    if config is None:
        config = KeyFormatConfig()

    if not key_input or not key_input.strip():
        return False, "", "Empty license key"

    cleaned = normalize_key_input(key_input, config)
    alphabet = config.get_alphabet()

    # Check alphabet characters
    for ch in cleaned:
        if ch not in alphabet:
            return False, "", f"Invalid character in license key: '{ch}'"

    # Check length
    if len(cleaned) != config.raw_length:
        return (
            False,
            "",
            f"Invalid key length: expected {config.raw_length} characters, got {len(cleaned)}",
        )

    # Checksum validation
    if config.checksum_type == ChecksumType.LUHN_MOD32:
        body = cleaned[:-1]
        check_char = cleaned[-1]
        expected = _compute_luhn_mod32_check_char(body, alphabet)
        if check_char != expected:
            return False, "", "Checksum validation failed (character typo detected)"
    elif config.checksum_type == ChecksumType.CRC8:
        body = cleaned[:-1]
        check_char = cleaned[-1]
        crc = _compute_crc8(body.encode("utf-8"))
        expected = alphabet[crc % len(alphabet)]
        if check_char != expected:
            return False, "", "CRC-8 checksum validation failed"

    return True, cleaned, ""
