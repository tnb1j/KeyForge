# KeyForge Offline Licensing Specification

## 1. How Offline Licensing Works

KeyForge achieves 100% offline license validation through asymmetric cryptography (Ed25519) and deterministic payload canonicalization (RFC 8785).

```text
 ┌────────────────────────────────────────────────────────┐
 │                   KEYFORGE ISSUER                      │
 │ 1. Assembles structured JSON claims payload            │
 │ 2. Computes deterministic RFC 8785 canonical bytes     │
 │ 3. Signs with Private Key: sig = Sign(privKey, bytes)  │
 │ 4. Bundles into .lic file or compact token             │
 └───────────────────────────┬────────────────────────────┘
                             │
                  Offline Distribution
                (.lic file, token, email)
                             │
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │                    OFFLINE CLIENT                      │
 │ 1. Reads license payload and signature                 │
 │ 2. Canonicalizes payload to RFC 8785 bytes             │
 │ 3. Verifies signature against embedded Public Key      │
 │ 4. Evaluates expiration, features, and version rules   │
 └────────────────────────────────────────────────────────┘
```

---

## 2. Token & File Formats

### A. Compact Armored Token (`.token`)
```text
kf1.<base64url_payload>.<base64url_signature>.<base64url_key_id>
```

### B. Signed License JSON File (`.lic`)
```json
{
  "schema_version": 1,
  "key_id": "key-v1-photostudio",
  "algorithm": "Ed25519",
  "payload": {
    "schema_version": 1,
    "license_id": "lic_photo_882",
    "license_key": "PHOTO-7K4M-9Q2X-8T6P",
    "product_id": "photostudio",
    "license_type": "subscription",
    "edition": "professional",
    "customer_id": "alice@creative.io",
    "issued_at": "2026-08-22T00:00:00Z",
    "expires_at": "2030-01-01T00:00:00Z",
    "features": ["ui", "raw_export", "batch_filter", "cloud_backup"],
    "max_devices": 3
  },
  "signature": "3da3a8c6a28099c9e212dfed6e79eada58575c2534a466ec485ed0bbeca722c0..."
}
```

---

## 3. Clock Manipulation Defense

The client SDK includes `ClockGuard`, which monitors monotonic timestamp progression:
* Records trusted UTC timestamps on each successful execution.
* If a user sets their system clock backwards in an attempt to extend an expired license, `ClockGuard` detects the backward jump and flags `CLOCK_ROLLBACK_DETECTED`.
