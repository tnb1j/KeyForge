# KeyForge Security Audit Checklist

| Item | Question | Verification Status | Rationale |
|---|---|---|---|
| **1** | Can a client create a valid license? | **NO** | Ed25519 asymmetric cryptography ensures signatures can only be produced with the private key on the server. |
| **2** | Is the private signing key exposed to clients? | **NO** | Client SDKs only contain or query public keys. Private keys never leave the server vault. |
| **3** | Can a license payload be modified without detection? | **NO** | Any alteration to the canonical JSON byte sequence causes signature validation to fail. |
| **4** | Can a revoked license remain valid indefinitely? | **NO** | Online checks immediately report REVOKED status; offline licenses can be bounded with short expiration or required heartbeats. |
| **5** | Can device activation limits be bypassed server-side? | **NO** | Server enforces strict atomic seat counting and rejects registrations exceeding `max_devices`. |
| **6** | Can an attacker brute-force license keys? | **NO** | 120 req/min sliding-window rate limiting + CSPRNG keys with error-detecting checksums. |
| **7** | Are secrets or private keys logged? | **NO** | Audit logger automatically redacts passwords, tokens, API keys, and private keys. |
| **8** | Are API endpoints properly authenticated? | **YES** | Admin routes protected by Argon2id + JWT / API Keys with RBAC enforcement. |
| **9** | Can local clock rollback bypass expiration? | **NO** | `ClockGuard` monitors monotonic timestamps and flags backward adjustments. |
| **10** | Can key rotation break existing valid licenses? | **NO** | Historical public keys are retained in the vault, allowing existing valid licenses to verify. |
