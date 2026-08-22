"""Unit tests for RFC 8785 JSON Canonicalization."""

import pytest
from keyforge.core.canonical import canonical_bytes, canonical_hash, canonical_json


def test_canonical_key_ordering():
    # Order of keys in dictionary should not affect output
    d1 = {"z": 1, "a": 2, "m": 3}
    d2 = {"a": 2, "m": 3, "z": 1}
    assert canonical_json(d1) == '{"a":2,"m":3,"z":1}'
    assert canonical_json(d1) == canonical_json(d2)


def test_nested_canonical_ordering():
    d1 = {"product": {"id": "app", "version": "1.0"}, "features": ["b", "a"]}
    d2 = {"features": ["b", "a"], "product": {"version": "1.0", "id": "app"}}
    assert canonical_json(d1) == canonical_json(d2)
    assert canonical_json(d1) == '{"features":["b","a"],"product":{"id":"app","version":"1.0"}}'


def test_compact_spacing():
    d = {"key": "value", "list": [1, 2, 3]}
    res = canonical_json(d)
    assert " " not in res
    assert res == '{"key":"value","list":[1,2,3]}'


def test_canonical_hash():
    d1 = {"b": 2, "a": 1}
    d2 = {"a": 1, "b": 2}
    h1 = canonical_hash(d1)
    h2 = canonical_hash(d2)
    assert len(h1) == 64
    assert h1 == h2
