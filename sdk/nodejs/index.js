/**
 * KeyForge Node.js / TypeScript Client SDK
 * 
 * Provides offline Ed25519 cryptographic validation and REST online activation
 * for Node.js servers, CLI tools, Electron desktop apps, and microservices.
 */

const crypto = require('node:crypto');
const os = require('node:os');

/**
 * Deterministic RFC 8785 canonical JSON serializer.
 */
function canonicalJson(data) {
  if (data === null || data === undefined) return 'null';
  if (typeof data === 'boolean' || typeof data === 'number') return JSON.stringify(data);
  if (typeof data === 'string') return JSON.stringify(data);
  if (Array.isArray(data)) {
    return '[' + data.map((item) => canonicalJson(item)).join(',') + ']';
  }
  if (typeof data === 'object') {
    const keys = Object.keys(data).sort();
    const entries = keys
      .filter((k) => data[k] !== undefined)
      .map((k) => JSON.stringify(k) + ':' + canonicalJson(data[k]));
    return '{' + entries.join(',') + '}';
  }
  return JSON.stringify(data);
}

function b64urlDecode(str) {
  const padded = str + '='.repeat((4 - (str.length % 4)) % 4);
  return Buffer.from(padded.replace(/-/g, '+').replace(/_/g, '/'), 'base64');
}

/**
 * Verify Ed25519 signature over canonical payload.
 */
function verifyEd25519(payload, signatureB64, publicKeyPemOrHex) {
  try {
    const messageBytes = Buffer.from(canonicalJson(payload), 'utf8');
    let publicKey;

    if (typeof publicKeyPemOrHex === 'string' && publicKeyPemOrHex.includes('BEGIN PUBLIC KEY')) {
      publicKey = crypto.createPublicKey(publicKeyPemOrHex);
    } else {
      const rawPub = Buffer.isBuffer(publicKeyPemOrHex)
        ? publicKeyPemOrHex
        : Buffer.from(publicKeyPemOrHex, 'hex');
      publicKey = crypto.createPublicKey({
        key: {
          kty: 'OKP',
          crv: 'Ed25519',
          x: rawPub.toString('base64url'),
        },
        format: 'jwk',
      });
    }

    const sigBytes = typeof signatureB64 === 'string' ? b64urlDecode(signatureB64) : signatureB64;
    return crypto.verify(null, messageBytes, publicKey, sigBytes);
  } catch (err) {
    return false;
  }
}

class KeyForgeNodeClient {
  constructor(options = {}) {
    this.productId = options.productId || 'default-product';
    this.publicKey = options.publicKey || null;
    this.serverUrl = options.serverUrl ? options.serverUrl.replace(/\/+$/, '') : null;
    this.clientVersion = options.clientVersion || '1.0.0';
    this.cachedLicense = null;
    this.lastResult = null;
  }

  /**
   * Parse an armored token (kf1.payload.sig.keyid)
   */
  parseToken(token) {
    const parts = token.trim().split('.');
    if (parts.length !== 4 || parts[0] !== 'kf1') {
      throw new Error('Invalid KeyForge armored token structure');
    }
    const payloadJson = b64urlDecode(parts[1]).toString('utf8');
    const payload = JSON.parse(payloadJson);
    const signature = parts[2];
    const keyId = b64urlDecode(parts[3]).toString('utf8');

    return {
      schema_version: 1,
      key_id: keyId,
      algorithm: 'Ed25519',
      payload,
      signature,
    };
  }

  /**
   * Validate a license offline or online.
   */
  async validate(licenseInput) {
    let signedLic;
    try {
      if (typeof licenseInput === 'string') {
        if (licenseInput.startsWith('kf1.')) {
          signedLic = this.parseToken(licenseInput);
        } else if (licenseInput.startsWith('{')) {
          signedLic = JSON.parse(licenseInput);
        } else {
          signedLic = { payload: { license_key: licenseInput, product_id: this.productId } };
        }
      } else if (typeof licenseInput === 'object') {
        signedLic = licenseInput;
      }
    } catch (err) {
      return {
        is_valid: false,
        status: 'INVALID_FORMAT',
        message: `Failed to parse license: ${err.message}`,
      };
    }

    // Offline validation if public key is supplied
    if (this.publicKey && signedLic && signedLic.signature && signedLic.payload) {
      const payload = signedLic.payload;

      // Product check
      if (payload.product_id && payload.product_id !== this.productId) {
        return {
          is_valid: false,
          status: 'PRODUCT_MISMATCH',
          message: `Product mismatch: expected ${this.productId}, got ${payload.product_id}`,
        };
      }

      // Signature verification
      const isSigValid = verifyEd25519(payload, signedLic.signature, this.publicKey);
      if (!isSigValid) {
        return {
          is_valid: false,
          status: 'INVALID_SIGNATURE',
          message: 'Ed25519 cryptographic signature verification failed (tampered or wrong key)',
        };
      }

      // Expiration check
      const now = new Date();
      let daysRemaining = null;
      if (payload.expires_at) {
        const expDate = new Date(payload.expires_at);
        if (now > expDate) {
          return {
            is_valid: false,
            status: 'EXPIRED',
            message: `License expired at ${payload.expires_at}`,
            expires_at: payload.expires_at,
            days_remaining: 0,
          };
        }
        daysRemaining = Math.max(0, Math.floor((expDate - now) / (1000 * 60 * 60 * 24)));
      }

      this.cachedLicense = signedLic;
      this.lastResult = {
        is_valid: true,
        status: 'VALID',
        message: 'License verified successfully offline',
        license_id: payload.license_id,
        product_id: payload.product_id,
        edition: payload.edition || 'standard',
        features: payload.features || [],
        expires_at: payload.expires_at || null,
        days_remaining: daysRemaining,
        allowed_devices: payload.max_devices || 1,
      };
      return this.lastResult;
    }

    // Online validation fallback
    if (this.serverUrl) {
      const keyStr = signedLic.payload ? signedLic.payload.license_key : licenseInput;
      const res = await fetch(`${this.serverUrl}/api/v1/licenses/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          license_key: keyStr,
          product_id: this.productId,
          client_version: this.clientVersion,
        }),
      });
      const result = await res.json();
      this.lastResult = result;
      return result;
    }

    return {
      is_valid: false,
      status: 'INVALID_SIGNATURE',
      message: 'Cannot validate: neither public key nor server URL provided',
    };
  }

  hasFeature(featureName) {
    if (!this.lastResult || !this.lastResult.is_valid) return false;
    const features = this.lastResult.features || [];
    return features.includes('*') || features.includes(featureName);
  }
}

module.exports = {
  KeyForgeNodeClient,
  canonicalJson,
  verifyEd25519,
};
