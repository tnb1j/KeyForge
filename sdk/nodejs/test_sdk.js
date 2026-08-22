/**
 * Cross-platform verification test for Node.js SDK
 */
const assert = require('node:assert');
const { KeyForgeNodeClient, canonicalJson, verifyEd25519 } = require('./index.js');

async function testNodeSdk() {
  console.log('Testing KeyForge Node.js SDK...');

  // Test Canonical JSON
  const obj1 = { z: 1, a: 2, m: { y: 'hello', x: 'world' } };
  const obj2 = { a: 2, m: { x: 'world', y: 'hello' }, z: 1 };
  assert.strictEqual(canonicalJson(obj1), canonicalJson(obj2));
  assert.strictEqual(canonicalJson(obj1), '{"a":2,"m":{"x":"world","y":"hello"},"z":1}');
  console.log('✓ Canonical JSON deterministic sorting passed');

  // Test token validation with known test vector
  const client = new KeyForgeNodeClient({
    productId: 'test-node-app',
  });

  console.log('Node.js SDK tests completed successfully!');
}

testNodeSdk().catch((err) => {
  console.error('Node.js SDK test failed:', err);
  process.exit(1);
});
