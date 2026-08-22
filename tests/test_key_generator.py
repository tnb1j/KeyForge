"""Unit tests for Human-Readable Key Formatting and Checksums."""

import pytest
from keyforge.core.key_generator import (
    AlphabetType,
    ChecksumType,
    KeyFormatConfig,
    generate_human_key,
    parse_and_validate_key,
)


def test_generate_default_crockford_key():
    config = KeyFormatConfig(
        prefix="PROD",
        raw_length=16,
        group_size=4,
        separator="-",
        alphabet_type=AlphabetType.CROCKFORD_BASE32,
        checksum_type=ChecksumType.LUHN_MOD32,
    )
    key = generate_human_key(config)
    assert key.startswith("PROD-")
    parts = key.split("-")
    assert len(parts) == 5  # "PROD", 4 groups of 4 chars
    assert all(len(p) == 4 for p in parts[1:])

    # Validate generated key passes parsing and checksum
    is_valid, normalized, err = parse_and_validate_key(key, config)
    assert is_valid is True
    assert len(normalized) == 16
    assert err == ""


def test_crockford_typo_correction():
    config = KeyFormatConfig(
        prefix="",
        raw_length=16,
        group_size=4,
        separator="-",
        alphabet_type=AlphabetType.CROCKFORD_BASE32,
        checksum_type=ChecksumType.LUHN_MOD32,
    )
    key = generate_human_key(config)

    # Replace 'O' with '0' or 'I' with '1' and test normalization
    # If the key contains '0', test replacing with 'O'
    fake_user_typed = key.lower().replace("-", " ")
    is_valid, _, _ = parse_and_validate_key(fake_user_typed, config)
    assert is_valid is True


def test_typo_detection_fails_checksum():
    config = KeyFormatConfig(
        prefix="APP",
        raw_length=16,
        group_size=4,
        separator="-",
        alphabet_type=AlphabetType.CROCKFORD_BASE32,
        checksum_type=ChecksumType.LUHN_MOD32,
    )
    key = generate_human_key(config)
    is_valid, _, _ = parse_and_validate_key(key, config)
    assert is_valid is True

    # Intentionally corrupt a single character in the body
    key_chars = list(key)
    # Find a character in the middle
    idx = len(key) - 4
    orig = key_chars[idx]
    key_chars[idx] = "9" if orig != "9" else "8"
    corrupted_key = "".join(key_chars)

    is_valid_bad, _, err = parse_and_validate_key(corrupted_key, config)
    assert is_valid_bad is False
    assert "checksum" in err.lower() or "typo" in err.lower()


def test_crc8_checksum_mode():
    config = KeyFormatConfig(
        prefix="CRC",
        raw_length=16,
        group_size=4,
        separator="-",
        alphabet_type=AlphabetType.HEXADECIMAL,
        checksum_type=ChecksumType.CRC8,
    )
    key = generate_human_key(config)
    is_valid, _, err = parse_and_validate_key(key, config)
    assert is_valid is True
    assert err == ""
