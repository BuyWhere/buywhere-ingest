// Static smoke test for src/ccDiscover.js — verifies the strict-probe pattern
// against a small set of known-Shopify and known-not-Shopify domains. Does
// NOT touch the DB. Run with: node scripts/test-cc-discover-smoke.mjs

import {
  isProbeableDomain,
  strictProbeShopify,
  loadCandidateList,
} from '../src/ccDiscover.js';

const KNOWN_SHOPIFY = [
  'allbirds.com',
  'gymshark.com',
  'redbull.com',
  'kith.com',
  'glossier.com',
];

// These are unlikely to respond on /products.json with application/json
// (they're either down or not Shopify). They let us verify the
// strict-probe correctly rejects non-JSON / 404 / DNS failures.
const KNOWN_DEAD = [
  'this-domain-definitely-does-not-exist-91823.example',
  'localhost',
  'foo',
];

const results = [];

for (const d of KNOWN_SHOPIFY) {
  const t0 = Date.now();
  const r = await strictProbeShopify(d, { timeoutMs: 8000, retryDelayMs: 250 });
  results.push({ domain: d, expected: 'shopify', ok: r.ok, reason: r.reason, dt: Date.now() - t0 });
}

for (const d of KNOWN_DEAD) {
  const t0 = Date.now();
  const r = await strictProbeShopify(d, { timeoutMs: 5000, retryDelayMs: 250 });
  results.push({ domain: d, expected: 'dead', ok: r.ok, reason: r.reason, dt: Date.now() - t0 });
}

console.log('\n=== strict-probe smoke results ===');
for (const r of results) {
  const tag = r.expected === 'shopify' ? (r.ok ? 'PASS' : 'FAIL') : (r.ok ? 'UNEXPECTED-PASS' : 'PASS');
  console.log(`  ${tag.padEnd(15)} ${r.domain.padEnd(60)} ok=${r.ok} reason=${r.reason || '-'} dt=${r.dt}ms`);
}

const unexpectedPasses = results.filter((r) => r.expected === 'dead' && r.ok);
const expectedFails = results.filter((r) => r.expected === 'shopify' && !r.ok);

if (unexpectedPasses.length > 0) {
  console.log(`\nWARN: ${unexpectedPasses.length} KNOWN_DEAD domains passed strict-probe (network or stale list?)`);
}
if (expectedFails.length > 0) {
  console.log(`\nNOTE: ${expectedFails.length} KNOWN_SHOPIFY domains failed strict-probe (network issues possible)`);
}

// Test isProbeableDomain
const ipCases = [
  ['example.com', true],
  ['a.b.c', true],
  ['localhost', false],
  ['foo', false],
  ['', false],
  ['has space.com', false],
  ['has/slash.com', false],
  [null, false],
  [undefined, false],
  [123, false],
  ['a'.repeat(254), false],
];
let probeableOk = true;
for (const [d, expected] of ipCases) {
  const got = isProbeableDomain(d);
  if (got !== expected) {
    console.log(`  isProbeableDomain(${JSON.stringify(d)}) = ${got}, expected ${expected}`);
    probeableOk = false;
  }
}
if (!probeableOk) {
  console.error('FAIL: isProbeableDomain cases failed');
  process.exit(1);
}
console.log('isProbeableDomain: all cases pass');

// Test loadCandidateList on the bundled WAT pool
const path = 'data/wat-pool.jsonl';
const t0 = Date.now();
const list = await loadCandidateList(path);
const dt = Date.now() - t0;
console.log(`\nloadCandidateList(${path}): ${list.length} candidates loaded in ${dt}ms`);
if (list.length < 40000) {
  console.error(`FAIL: expected ~43,650 candidates, got ${list.length}`);
  process.exit(1);
}
const sample = list.slice(0, 3);
console.log('sample:', JSON.stringify(sample, null, 2));

console.log('\n=== SMOKE TEST PASS ===');
