# KeyForge Architectural Specification

## 1. System Overview

**KeyForge** is a universal, adaptive software licensing and cryptographic key management framework designed to decouple licensing policy and cryptographic verification from product-specific implementations.

```text
 ┌─────────────────────────────────────────────────────────────────────────┐
 │                           ADMIN / OPERATOR                              │
 └──────────────────────┬────────────────────────────┬─────────────────────┘
                        │                            │
                        ▼                            ▼
             ┌─────────────────────┐      ┌────────────────────┐
             │  Web Admin Console  │      │ Administrative CLI │
             └──────────┬──────────┘      └──────────┬─────────┘
                        │                            │
                        ▼                            ▼
 ┌─────────────────────────────────────────────────────────────────────────┐
 │                       KEYFORGE SERVER & REST API                        │
 │  ┌───────────────────────────────────────────────────────────────────┐  │
 │  │ API Endpoints: /licenses, /activate, /validate, /products, /keys   │  │
 │  ├───────────────────────────────────────────────────────────────────┤  │
 │  │ Security: Argon2id Auth, API Key Tokens, Rate Limiter, Audit Log  │  │
 │  ├───────────────────────────────────────────────────────────────────┤  │
 │  │ Engines: Policy Evaluator, Key Generator, Ed25519 Signer/Verifier │  │
 │  └───────────────────┬────────────────────────────┬──────────────────┘  │
 └──────────────────────┼────────────────────────────┼─────────────────────┘
                        │                            │
                        ▼                            ▼
              ┌───────────────────┐        ┌───────────────────┐
              │ Database / Store  │        │ Crypto Key Vault  │
              │ (SQLite / Postgres)│       │ (Ed25519 Keypairs)│
              └───────────────────┘        └───────────────────┘
                        │                            │
                        └─────────────┬──────────────┘
                                      │
       ┌──────────────────────────────┴──────────────────────────────┐
       │                                                             │
       ▼                                                             ▼
┌───────────────────────────────┐             ┌───────────────────────────────┐
│     ONLINE CLIENT SDK         │             │      OFFLINE CLIENT SDK       │
│  (Python, Node, PS, C#, Go)   │             │   (Public Key Verification)   │
├───────────────────────────────┤             ├───────────────────────────────┤
│ • API Activation & Heartbeat  │             │ • Detached / Embedded Sig     │
│ • Device Fingerprint Binding  │             │ • Tamper Detection            │
│ • Revocation & Renewal Sync   │             │ • Clock-Rollback Defense      │
│ • Secure Local License Cache  │             │ • Offline Grace Period Check  │
└───────────────────────────────┘             └───────────────────────────────┘
```

---

## 2. Component Separation & Responsibilities

1. **Key/License Generator**: Produces high-entropy cryptographic keys, applies custom formatting (e.g. Crockford Base32 with Luhn mod-32 checksums), and constructs immutable claims.
2. **Canonical Serializer**: Serializes structured JSON payload into RFC 8785 canonical bytes for deterministic signing.
3. **Cryptographic Vault**: Manages active, rotated, and historical Ed25519 keypairs. Signs payloads on the server; distributes public verification keys to clients.
4. **Validation Engine**: Executes a 12-step validation sequence evaluating signature authenticity, product matching, expiration, feature entitlements, version constraints, and seat counts.
5. **REST API**: Provides authenticated endpoints for administration, product catalog management, license issuance, online activation, heartbeats, and audit trails.
6. **Web Dashboard**: Responsive administration interface for metrics, product configuration, seat resets, and key rotation.
7. **Client SDKs**: Reusable client libraries across Python, Node.js, PowerShell, C#, and Go with pluggable storage adapters (Windows DPAPI, encrypted files) and clock-rollback guards.
