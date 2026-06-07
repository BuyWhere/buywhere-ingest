// Module-import smoke for src/ccDiscover.js — exercises the module's
// top-level exports without touching the network or the DB. Run with:
//   node scripts/test-cc-discover-import.mjs

import {
  isProbeableDomain,
  strictProbeShopify,
  probeDomainsStrict,
  loadCandidateList,
} from '../src/ccDiscover.js';

const required = ['isProbeableDomain', 'strictProbeShopify', 'probeDomainsStrict', 'loadCandidateList'];
for (const name of required) {
  if (typeof eval(name) !== 'function') {
    console.error(`FAIL: ${name} is not a function (got ${typeof eval(name)})`);
    process.exit(1);
  }
}
console.log('ccDiscover.js exports: all 4 functions present and callable');

// Dry-run: probeDomainsStrict with a tiny in-memory list
const dry = await probeDomainsStrict(['example.com', 'this-does-not-exist-12345.invalid'], {
  concurrency: 2,
  timeoutMs: 4000,
  retryDelayMs: 200,
});
console.log('dry-run probe stats:', JSON.stringify(dry.stats));
if (dry.stats.probed !== 2) {
  console.error('FAIL: dry-run probed != 2');
  process.exit(1);
}
if (!(dry.results.get('example.com'))) {
  console.error('FAIL: dry-run missing result for example.com');
  process.exit(1);
}
if (!(dry.results.get('this-does-not-exist-12345.invalid'))) {
  console.error('FAIL: dry-run missing result for invalid domain');
  process.exit(1);
}

console.log('\n=== IMPORT SMOKE TEST PASS ===');
