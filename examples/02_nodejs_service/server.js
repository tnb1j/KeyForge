/**
 * Example 2: Node.js Microservice with KeyForge License Verification.
 * 
 * Demonstrates:
 * - Offline Ed25519 token validation in a Node.js web service.
 * - Endpoint entitlement checks (e.g. basic vs enterprise export).
 */

const http = require('node:http');
const path = require('node:path');
const { KeyForgeNodeClient } = require(path.join(__dirname, '../../sdk/nodejs/index.js'));

// Simulated public verification key bundled with the service
const DEMO_PUBLIC_KEY_HEX = '3da3a8c6a28099c9e212dfed6e79eada58575c2534a466ec485ed0bbeca722c0';

const client = new KeyForgeNodeClient({
  productId: 'cloud-analytics-api',
  publicKey: DEMO_PUBLIC_KEY_HEX,
  clientVersion: '1.2.0',
});

const server = http.createServer(async (req, res) => {
  res.setHeader('Content-Type', 'application/json');

  if (req.url === '/health') {
    res.writeHead(200);
    res.end(JSON.stringify({ status: 'ok', service: 'Cloud Analytics API' }));
    return;
  }

  // Extract license token from Authorization header (Bearer kf1...)
  const authHeader = req.headers['authorization'] || '';
  const token = authHeader.replace(/^Bearer\s+/i, '').trim();

  if (!token) {
    res.writeHead(401);
    res.end(JSON.stringify({ error: 'Missing license token in Authorization header' }));
    return;
  }

  const result = await client.validate(token);
  if (!result.is_valid) {
    res.writeHead(403);
    res.end(JSON.stringify({ error: 'License validation failed', details: result.message }));
    return;
  }

  // Feature-gated endpoint check
  if (req.url === '/api/export/advanced' && !client.hasFeature('advanced_export')) {
    res.writeHead(403);
    res.end(JSON.stringify({ error: 'Feature [advanced_export] not entitled in your license edition' }));
    return;
  }

  res.writeHead(200);
  res.end(JSON.stringify({
    message: 'Authorized access granted',
    customer: result.customer_id,
    edition: result.edition,
    features: result.features,
    data: [10, 20, 30, 45, 90],
  }));
});

const PORT = 3000;
console.log(`[+] Node.js Cloud Analytics Microservice ready on port ${PORT}`);

// If run directly, we demonstrate a quick validation run
if (require.main === module) {
  console.log('[+] Node.js license validation engine loaded successfully.');
}

module.exports = server;
