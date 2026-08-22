# KeyForge Configuration & Profiles Guide

## 1. Declarative Product Configuration

KeyForge is configuration-driven. Every software product defines its policies in a JSON configuration profile.

```json
{
  "product": {
    "id": "photostudio",
    "name": "PhotoStudio Pro",
    "version": "2.4.0",
    "description": "Professional Desktop Image Suite"
  },
  "key_format": {
    "prefix": "PHOTO",
    "suffix": "",
    "raw_length": 16,
    "group_size": 4,
    "separator": "-",
    "alphabet_type": "CROCKFORD_BASE32",
    "checksum_type": "LUHN_MOD32",
    "case_sensitive": false
  },
  "activation": {
    "enabled": true,
    "max_devices_default": 3,
    "require_online_activation": false,
    "heartbeat_interval_seconds": 86400,
    "offline_grace_period_days": 14
  },
  "expiration": {
    "allow_lifetime": true,
    "default_subscription_days": 365,
    "default_trial_days": 14
  },
  "features": {
    "available_features": ["ui", "raw_export", "batch_filter", "cloud_backup"],
    "default_features": ["ui"],
    "editions": {
      "standard": ["ui", "raw_export"],
      "professional": ["ui", "raw_export", "batch_filter", "cloud_backup"],
      "enterprise": ["*"]
    }
  },
  "security": {
    "signature_algorithm": "Ed25519",
    "min_key_version": 1,
    "allow_offline_validation": true,
    "enable_clock_guard": true
  }
}
```

---

## 2. Built-in Profile Presets

* **`desktop`**: Tailored for desktop applications. Supports offline verification, bundled public key, 3 seats per license, and 14-day offline grace period.
* **`saas_api`**: Tailored for cloud microservices and developer APIs. Online validation required, seat and quota tracking, short heartbeat interval.
* **`air_gapped`**: Tailored for high-security, isolated offline networks. Signed `.lic` file distribution, zero outbound network connectivity required.
