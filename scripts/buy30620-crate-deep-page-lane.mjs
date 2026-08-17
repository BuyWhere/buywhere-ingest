#!/usr/bin/env node
// BUY-30620 Crate — deep page (8 pages) fresh merchants, high-fidelity ingest
import { appendFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'fs';
import { fetchAllProducts, fetchShopCurrency, headProductsEndpoint, toProductRecord, computeMerchantFabricationSignals, DEFAULT_MERCHANT_FABRICATION_THRESHOLDS, ensureDir } from './lib/buy30619-discovery-common.mjs';
import { uploadAndMark } from './lib/lane_r2_teardown.mjs';

const ROOT = '/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c';
const FEED = `${ROOT}/data/google_shopping_merchants.jsonl`;
const TRANCO_FEED = `${ROOT}/data/tranco_fresh_injection.jsonl`;
const PRODUCTIVE_FEED = `${ROOT}/data/productive_feeds/crate.ndjson`;
const PRODUCTIVE_ONLY = process.env.CRATE_PRODUCTIVE_ONLY !== 'false'; // set to 'false' to use full feed
const OUT_DIR = `${ROOT}/data/buy30620-crate`;
const CKPT = `${OUT_DIR}/checkpoint.json`;
const LOG = `${ROOT}/logs/buy30620_crate.log`;
const R2_TEARDOWN_LOG = `${ROOT}/logs/buy30620_crate_r2.log`;
const LANE = 'crate';
const LANE_SOURCE = 'shopify_buy30620_crate';
const CONCURRENCY = parseInt(process.env.BD_CONCURRENCY_web_unlocker2 || '20', 10);
const MAX_PAGES = 8;
const BATCH = 200;
const SLEEP_MS = 4000;
const DEAD_ZONE_THRESHOLD = 5;       // skip-ahead after this many consecutive 0-product cycles
const SKIP_MIN = 2000;             // minimum random jump forward
const SKIP_RANGE = 5000;
const GS_FEED_DOMAIN_COUNT = 327719;             // maximum random jump forward range (positions)

function log(msg) {
  const line = `[${new Date().toISOString()}] ${msg}`;
  console.error(line);
  try { appendFileSync(LOG, line + '\n'); } catch {}
}

function throughputWindowThrottleMs() {
  // BUY-70955: disabled — this throttle was pausing production for the first
  // 20 minutes of every hour, leaving the drain with no work and causing
  // genuine hourly throughput failures. Rollback if needed:
  //   BUY64173_DISABLE_THROTTLE=1 node scripts/buy30620-crate-deep-page-lane.mjs
  if (process.env.BUY64173_DISABLE_THROTTLE === '1') return 0;
  return 0;
}

function loadFeed() {
  // BUY-61766: Prefer the productive-source feed which excludes zero-yield
  // Shopify stores that have never produced a product. Falls back to the
  // full feed when the productive feed doesn't exist.
  const productiveFeed = existsSync(PRODUCTIVE_FEED) && PRODUCTIVE_ONLY;
  const feeds = productiveFeed ? [PRODUCTIVE_FEED] : [FEED, TRANCO_FEED];
  const domains = [];
  const seen = new Set();
  for (const feed of feeds) {
    if (!existsSync(feed)) continue;
    for (const line of readFileSync(feed, 'utf-8').split('\n')) {
      if (!line.trim()) continue;
      try {
        const parsed = JSON.parse(line);
        const d = parsed.domain;
        if (d && !seen.has(d)) { seen.add(d); domains.push(d); }
      } catch {}
    }
  }
  return domains;
}
function loadCkpt() {
  if (!existsSync(CKPT)) return { cursor: 0, cycle: 0, ingested: 0 };
  try { return JSON.parse(readFileSync(CKPT, 'utf-8')); }
  catch { return { cursor: 0, cycle: 0, ingested: 0 }; }
}
function saveCkpt(c) { writeFileSync(CKPT, JSON.stringify(c)); }

async function deepPageMerchant(domain) {
  const head = await headProductsEndpoint(domain, { timeoutMs: 5000 });
  if (!head.headPositive) return null;
  const products = await fetchAllProducts(domain, { timeoutMs: 10000, maxPages: MAX_PAGES });
  if (!products || products.length === 0) return null;
  const signals = computeMerchantFabricationSignals(products, DEFAULT_MERCHANT_FABRICATION_THRESHOLDS);
  if (signals.alerts.length > 0) {
    log(`SKIP ${domain}: ${signals.alerts.join(', ')}`);
    return null;
  }
  const currency = await fetchShopCurrency(domain, { timeoutMs: 5000 });
  if (!currency) {
    log(`SKIP ${domain}: Shopify currency unavailable`);
    return null;
  }
  return products.map(p => toProductRecord(domain, LANE_SOURCE, p, { lane: 'crate', currency }));
}

async function runCycle(domains, ckpt) {
  const start = ckpt.cursor % domains.length;
  const batch = [];
  for (let i = 0; i < BATCH; i++) batch.push(domains[(start + i) % domains.length]);
  ckpt.cursor = (start + BATCH) % domains.length;
  ckpt.cycle++;

  ensureDir(OUT_DIR);
  const ts = new Date().toISOString().replace(/[:.]/g, '-');
  const outFile = `${OUT_DIR}/cycle-${ckpt.cycle}-${ts}.ndjson`;
  writeFileSync(outFile, '');

  let total = 0, hits = 0;
  for (let i = 0; i < batch.length; i += CONCURRENCY) {
    const slice = batch.slice(i, i + CONCURRENCY);
    const results = await Promise.allSettled(slice.map(d => deepPageMerchant(d)));
    const lines = [];
    for (const r of results) {
      if (r.status !== 'fulfilled' || !r.value) continue;
      hits++;
      lines.push(...r.value);
      total += r.value.length;
    }
    if (lines.length) appendFileSync(outFile, lines.map(l => JSON.stringify(l)).join('\n') + '\n');
  }
  log(`crate cycle ${ckpt.cycle}: ${batch.length} domains → ${hits} hit → ${total} products → ${outFile}`);
  ckpt.ingested += total;
  saveCkpt(ckpt);
  return outFile;
}

function fireR2Teardown(outFile) {
  uploadAndMark({ localPath: outFile, lane: LANE, log: (m) => {
    log(m);
    try { appendFileSync(R2_TEARDOWN_LOG, `[${new Date().toISOString()}] ${m}\n`); } catch {}
  } }).catch((e) => log(`crate r2_teardown error: ${e.message || e}`));
}

async function main() {
  let domains = loadFeed();
  log(`crate loaded ${domains.length} fresh merchants`);
  const ckpt = loadCkpt();
  log(`crate starting cursor=${ckpt.cursor} cycle=${ckpt.cycle}`);
  let consecutiveEmpty = 0;
  while (true) {
    const throttleMs = throughputWindowThrottleMs();
    if (throttleMs > 0) {
      log(`BUY-64173 throttle: pausing crate Shopify refresh for ${Math.ceil(throttleMs / 1000)}s during throughput window rollback=BUY64173_DISABLE_THROTTLE=1`);
      await new Promise(r => setTimeout(r, throttleMs));
      continue;
    }
        if (ckpt.cycle > 0 && ckpt.cycle % 200 === 0) { try { const d = loadFeed(); if (d.length) { domains = d; log('crate reloaded ' + d.length + ' domains from feed'); } } catch {} }
    let outFile = null;
    const ingestedBefore = ckpt.ingested;
    try { outFile = await runCycle(domains, ckpt); }
    catch (e) { log(`crate cycle error: ${e.message}`); }
    if (outFile) fireR2Teardown(outFile);

    // Dead-zone skip-ahead: track consecutive empty cycles and jump cursor forward
    const produced = ckpt.ingested - ingestedBefore;
    if (produced === 0) {
      consecutiveEmpty++;
      if (consecutiveEmpty >= DEAD_ZONE_THRESHOLD && domains.length > 0) {
        const isInTrancoZone = ckpt.cursor >= GS_FEED_DOMAIN_COUNT || (ckpt.cursor + BATCH * Math.ceil(BATCH / CONCURRENCY)) >= GS_FEED_DOMAIN_COUNT;
        let skip;
        if (isInTrancoZone) {
          skip = 0 - ckpt.cursor;
          ckpt.cursor = 0;
        } else {
          skip = SKIP_MIN + Math.floor(Math.random() * (SKIP_RANGE - SKIP_MIN));
          ckpt.cursor = (ckpt.cursor + skip) % domains.length;
        }
        log(`crate DEAD-ZONE SKIP: ${consecutiveEmpty} empty cycles${isInTrancoZone ? ' (TRANCO ZONE)' : ''} -> cursor -> ${ckpt.cursor}`);
        saveCkpt(ckpt);
        consecutiveEmpty = 0;
      }
    } else {
      consecutiveEmpty = 0;
    }

    await new Promise(r => setTimeout(r, SLEEP_MS));
  }
}

main().catch(e => { log(`FATAL: ${e.message}`); process.exit(1); });
