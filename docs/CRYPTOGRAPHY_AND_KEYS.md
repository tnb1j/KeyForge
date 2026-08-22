# Cryptography and Key Management Guide

## 1. Cryptographic Primitives

KeyForge uses industry-standard asymmetric digital signatures:

* **Signature Algorithm**: **Ed25519** (RFC 8032 / Edwards-curve Digital Signature Algorithm over Curve25519).
* **Security Strength**: ~128-bit security level, resistant to side-channel attacks and signature malleability.
* **Deterministic Signatures**: Ed25519 uses deterministic nonce generation derived from the private key and message hash, eliminating the risk of bad random number generators leaking private keys during signing.
* **Payload Serialization**: **RFC 8785 (JSON Canonicalization Scheme - JCS)** ensuring bit-exact cross-platform byte alignment across Python, Node.js, C#, Go, and other environments.
* **Hash Functions**: SHA-256 for fingerprints, message digests, and checksum validations.
* **Randomness**: Operating system CSPRNG (`secrets` module in Python, `crypto.randomBytes` in Node.js).

---

## 2. Asymmetric Separation Model

```text
       SERVER / ISSUER                       CLIENT APPLICATION
 ┌─────────────────────────┐             ┌─────────────────────────┐
 │   Private Signing Key   │             │  Public Verification Key│
 │ (Never leaves backend)  │             │ (Safe to bundle in app) │
 └────────────┬────────────┘             └────────────▲────────────┘
              │                                       │
              ▼                                       │
      Canonical Claims                                │
              │                                       │
              ▼                                       │
      Ed25519 Sign()                                  │
              │                                       │
              ▼                                       │
   [ Signed License Token ] ──────────────────────────┘
                              VerifySignature()
```

* **Public Verification Key**: May be bundled in client binaries, distributed in `.lic` files, or fetched over TLS. Cannot be used to forge licenses.
* **Private Signing Key**: Stored securely on the server or hardware security module (HSM). Never embedded in client code or frontend scripts.

---

## 3. Key Rotation Lifecycle

When a product's signing key is rotated:
1. A new Ed25519 keypair is generated with an incremented version number ($v_{n+1}$).
2. The previous key is transitioned to `rotated` status in the vault.
3. Newly issued licenses are signed with the active $v_{n+1}$ private key.
4. Existing licenses previously signed with $v_n$ remain valid because clients retain or query the trusted historical public keys in the public vault.
5. In case of emergency key compromise, a key's status can be transitioned to `revoked`, causing the validation engine to reject all licenses signed by the compromised key.
