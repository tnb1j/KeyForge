# KeyForge: Universal Adaptive Software Key & License Management Platform

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com)
[![Cryptography](https://img.shields.io/badge/cryptography-Ed25519-green.svg)](https://cryptography.io)
[![Tests](https://img.shields.io/badge/tests-39%20passed-brightgreen.svg)]()
[![License](https://img.shields.io/badge/license-MIT-purple.svg)]()

**KeyForge** is a production-grade, universal, configurable software licensing and cryptographic key management platform. Designed from first principles as a reusable enterprise framework, KeyForge enables any software application (Desktop, Web API, CLI tool, Windows automation, plugins, mobile, embedded) to implement state-of-the-art software licensing through declarative configuration.

---

## 🌟 Key Architecture & Capabilities

* **Asymmetric Digital Signatures**: Pure **Ed25519** asymmetric cryptography (RFC 8032) ensuring private signing keys remain strictly in the secure backend vault while clients verify signatures offline or online using public verification keys.
* **Deterministic Canonical Serialization**: Strict **RFC 8785 (JSON Canonicalization Scheme - JCS)** ensures cross-language, bit-exact cryptographic signature alignment across Python, Node.js, C#, Go, PowerShell, and C++.
* **Flexible Human-Readable Key Formats**: Configurable key formatting (Crockford Base32, alphanumeric, custom alphabets, grouping, prefixes) with error-detecting **Luhn Mod-32** and **CRC-8** check digits to eliminate user typos.
* **Comprehensive License Types**:
  * **Trial Licenses**: Configurable duration (e.g. 14-day).
  * **Lifetime Licenses**: Perpetual authorization.
  * **Subscription Licenses**: Periodic renewals with cryptographic re-signing.
  * **Feature-Based Licenses**: Granular entitlement flags (`has_feature('export_pdf')`).
  * **Device & Seat-Bound Licenses**: Hardware/installation limits with online seat tracking and deactivation.
  * **Organization / User-Bound Licenses**: Tenant and account binding.
  * **Hybrid Licenses**: Any arbitrary combination defined by configuration profiles.
* **Online & Offline Validation**:
  * **Online**: REST API activation, seat limits, periodic heartbeats, remote suspension, and instant revocation.
  * **Offline**: Zero-network signature verification, tamper detection, and anti-clock-rollback tracking (`ClockGuard`).
* **Multi-Version Key Vault & Rotation**: Automated key rotation supporting multiple active verification keys during migration without breaking legacy issued licenses.
* **High-Performance REST API & Admin Console**: Built with FastAPI, OpenAPI 3.1, SQLite/PostgreSQL persistence, Argon2id password hashing, sliding-window rate limiting, and structured audit trails.
* **Multi-Language Client SDKs**: Official reference libraries for Python, Node.js/TypeScript, Windows PowerShell, C#/.NET, and Go.

---

## 📐 Conceptual Architecture

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

## 🚀 Quick Start Guide

### 1. Install Dependencies
```bash
python -m pip install -r requirements.txt
```

### 2. Start the KeyForge Server
```bash
python -m keyforge.cli serve --port 8000
```
* **Interactive Admin Dashboard**: [http://127.0.0.1:8000/dashboard](http://127.0.0.1:8000/dashboard)
* **Interactive OpenAPI Swagger**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **Default Admin Credentials**: `admin` / `KeyForgeAdmin2026!`

---

## 🛠️ Administrative CLI

KeyForge includes a full-featured CLI:

```bash
# Start server
python -m keyforge.cli serve --host 127.0.0.1 --port 8000

# List registered products
python -m keyforge.cli products list

# List cryptographic signing keys
python -m keyforge.cli keys list

# Issue a license
python -m keyforge.cli issue --product desktop-app --customer alice@company.com --edition pro --devices 3

# Inspect a license token
python -m keyforge.cli inspect "kf1.eyJjdXN0b21lci...3da3a8c6"
```

---

## 💻 Client SDK Integration Examples

### Python Desktop / CLI
```python
from keyforge_client import KeyForgeClient, FileLicenseStorage

client = KeyForgeClient(
    product_id="photostudio",
    public_key="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----",
    storage=FileLicenseStorage(),
)

if client.is_valid():
    print(f"Active Edition: {client.get_edition()}")
    if client.has_feature("raw_export"):
        enable_raw_export()
else:
    client.activate("PHOTO-7K4M-9Q2X-8T6P")
```

### Node.js / TypeScript
```javascript
const { KeyForgeNodeClient } = require('@keyforge/client');

const client = new KeyForgeNodeClient({
  productId: 'cloud-analytics-api',
  publicKey: '3da3a8c6a28099c9e212dfed6e79eada58575c2534a466ec485ed0bbeca722c0',
});

const result = await client.validate(token);
if (result.is_valid && client.hasFeature('advanced_export')) {
  // Allow API access
}
```

### Windows PowerShell
```powershell
Import-Module .\sdk\powershell\KeyForge.psm1

# Activate and validate
Invoke-KeyForgeActivation -ServerUrl "http://127.0.0.1:8000" -ProductId "desktop-app" -LicenseKey "DSK-XXXX-XXXX-XXXX"
$status = Test-KeyForgeLicense -ServerUrl "http://127.0.0.1:8000" -ProductId "desktop-app" -LicenseKey "DSK-XXXX-XXXX-XXXX"
```

---

## 🧪 Comprehensive Verification Suite

Run the full automated test suite covering unit tests, cryptographic verification, canonicalization, API integration, seat limits, rate limiting, and negative tamper testing:

```bash
python -m pytest tests/ -v
```

---

## 📚 Technical Documentation Suite

* [Architecture Specification](docs/ARCHITECTURE.md)
* [Cryptography & Key Management Guide](docs/CRYPTOGRAPHY_AND_KEYS.md)
* [Security Threat Model](docs/THREAT_MODEL.md)
* [REST API Reference](docs/API_REFERENCE.md)
* [Configuration & Profiles Guide](docs/CONFIGURATION_GUIDE.md)
* [Client Integration Guide](docs/CLIENT_INTEGRATION_GUIDE.md)
* [Offline Licensing Specification](docs/OFFLINE_LICENSING.md)
* [Vercel 100% Free-Tier Deployment Guide](docs/VERCEL_DEPLOYMENT.md)
* [Deployment & Disaster Recovery Guide](docs/DEPLOYMENT_AND_RECOVERY.md)
* [Security Audit Checklist](docs/SECURITY_AUDIT_CHECKLIST.md)

---

## ☁️ 100% Free-Tier Vercel Deployment

Deploy KeyForge directly to Vercel with a free serverless cloud PostgreSQL database (Neon or Supabase):

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/tnb1j/KeyForge&env=KEYFORGE_DB_URL,KEYFORGE_JWT_SECRET,KEYFORGE_ADMIN_USER,KEYFORGE_ADMIN_PASS)

See the complete step-by-step guide in [docs/VERCEL_DEPLOYMENT.md](docs/VERCEL_DEPLOYMENT.md).

---

## 📄 License

This project is open source software licensed under the **[MIT License](LICENSE)**.
Copyright (c) 2026 tnb1j (KeyForge Architecture Team).
