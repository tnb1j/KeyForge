# KeyForge Security Threat Model

## 1. Threat Analysis Framework

| Threat Vector | Attack Description | Mitigation in KeyForge |
|---|---|---|
| **License Forgery** | Attacker creates a custom license granting unentitled features or lifetime expiration. | **Mitigated**: Ed25519 asymmetric signatures prevent license creation without the server-side private key. |
| **Payload Tampering** | Attacker modifies claims (e.g. changes `edition: standard` to `enterprise`). | **Mitigated**: RFC 8785 canonical hash check fails signature verification immediately. |
| **Key Extraction** | Attacker extracts cryptographic keys from client code. | **Mitigated**: Client applications ONLY contain public verification keys. Private keys never leave the server vault. |
| **Cross-Product Reuse** | Attacker uses a valid license from Product A on Product B. | **Mitigated**: `product_id` is cryptographically signed inside payload and checked strictly in Step 4. |
| **Replay & Over-Activation** | Attacker activates 100 machines using a 1-device license. | **Mitigated**: Server enforces unique installation ID registrations and strictly blocks activations when count $\ge$ limit. |
| **Clock Rollback Attack** | Attacker sets system clock backwards to prevent license expiration. | **Mitigated**: `ClockGuard` records monotonic timestamps and detects backwards clock movement. |
| **Brute-Force Key Guessing** | Attacker floods API trying random keys. | **Mitigated**: Sliding-window rate limiter (120 req/min per IP) + high entropy CSPRNG keys with error-detecting checksums. |
| **Database Compromise** | Attacker dumps database to steal admin credentials. | **Mitigated**: Administrator passwords hashed with memory-hard Argon2id; API keys stored as SHA-256 digests. |

---

## 2. Honest Security Boundaries

> [!CAUTION]
> **Fundamental Client-Side DRM Reality**:
> No software licensing framework running on client hardware can guarantee 100% resistance against a determined reverse engineer who has full administrative control over the machine and uses debuggers or memory patchers.
> 
> KeyForge guarantees:
> 1. **Cryptographic Authenticity**: Unauthorized parties cannot issue valid licenses without the private signing key.
> 2. **Server-Side Authority**: Online activation limits, revocations, and seat quotas are strictly enforced server-side.
> 3. **Tamper Detection**: Altering any license claim invalidates the digital signature.
