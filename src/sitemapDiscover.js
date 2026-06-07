// BUY-34837: Sitemap-driven merchant discovery.
//
// Replaces the live Oracle-workspace scripts
//   scripts/buy30590-brand-sitemap-miner.mjs (13 brand domains)
//   scripts/buy30590-retailer-sitemap-miner.mjs (9 retailer domains, walked
//     by scripts/buy30590-retailer-sitemap-loop.mjs)
// with a first-class pgboss queue (`discover.sitemap`) in the buywhere-ingest
// worker. The original scripts discovered product URLs from XML sitemaps and
// either scraped the URLs inline (brand lane) or wrote them to JSONL for a
// downstream scraper (retailer lane). The replacement focuses on the upstream
// job: discover *merchants* that have a real product sitemap. Once a merchant
// is INSERTed into the `merchants` table with `source='sitemap_<kind>'` and
// `onboarding_stage='discovered'`, the existing `scrape.shopify` /
// `scrape.woocommerce.deep` cron producers (BUY-33632 / BUY-34834) pick it
// up on the next tick and enqueue the actual catalog-scrape jobs.
//
// Pipeline shape (mirrors trancoDiscovery.js and ccDiscover.js):
//   * Producer (one-shot CLI, daily cron on Railway):
//       reads a hand-curated seed list (data/brands.json or data/retailers.json),
//       enqueues one `discover.sitemap` job per (domain, sitemap_url, kind).
//   * Worker (long-running, buywhere-ingest-worker service):
//       fetches the sitemap URL, walks the sitemapindex if present, parses
//       <url><loc> entries, filters to product-shaped paths, and INSERTs
//       the *domain* (not the product URLs) into the `merchants` table on
//       the canonical BuyWhere DB. Product URL count is recorded in the
//       ingestion_runs row for monitoring.
//
// This module is worker-side only — the producer lives in
// src/producer-sitemap.js. The split mirrors the BUY-34833/34834 deep-page
// migration (worker module + producer module) and the BUY-34835/34836
// discovery migration (ccDiscover.js / trancoDiscovery.js).

import { DOMParser } from 'xmldom';
import { gunzipSync } from 'zlib';
import { readFileSync, existsSync } from 'fs';

// BUY-34837: same per-request timeout the live retailer-sitemap-miner used.
// Sitemaps can be large but most are < 5MB; 20s is plenty for the median
// and short enough that a stuck connection can't poison the worker.
const DEFAULT_FETCH_TIMEOUT_MS = 20000;

// BUY-34837: cap on total <url><loc> entries we walk before bailing. A
// runaway sitemap (or a sitemapindex that doesn't terminate) can't drag
// the worker forever. The 50k cap is well above the largest known brand
// sitemap (Nike ~20k product URLs) but small enough to bound memory.
const DEFAULT_MAX_LOCS = 50000;

// BUY-34837: how deep we recurse into a sitemapindex. The sitemaps.org
// spec allows arbitrary nesting, but in practice 2-3 levels cover
// sitemapindex → sitemap → urlset. The cap exists for safety.
const DEFAULT_MAX_DEPTH = 4;

// BUY-34837: minimum product-shaped <loc> count to consider a merchant
// "verified" — a merchant with 0 product URLs in its sitemap shouldn't
// be added to the queue. 1 is too permissive (a single sitemaps.org
// example URL trips it); 5 is the floor below which a sitemap looks
// empty enough to be a placeholder.
const MIN_PRODUCT_URLS_TO_VERIFY = 5;

// BUY-34837: two UA modes. Most brands/retailers serve sitemaps to a
// bot UA without complaint; a few (Macy's, Home Depot, Lowes per
// buy30590-retailer-sitemap-miner.mjs) 403 the bot UA and need a
// desktop UA. The seed list carries the `uaMode` per entry.
const BOT_UA = 'Mozilla/5.0 (compatible; BuywhereSitemapBot/1.0; +https://buywhere.example/bot)';
const DESKTOP_UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36';

function pickUA(mode) {
  return mode === 'desktop' ? DESKTOP_UA : BOT_UA;
}

/**
 * Fetch a sitemap URL and return the decoded XML text.
 * Handles three gzip-encoding cases (the buy30590-retailer-sitemap-miner
 * gunzip-support notes are the source of truth for the logic):
 *   1. content-encoding: gzip → fetch already decoded, return as text
 *   2. URL ends in .gz → gunzip the buffer
 *   3. content-type: gzip → gunzip the buffer
 *   4. magic bytes 1f 8b → gunzip the buffer
 *
 * Returns `{ ok, status, text, error, isGz, ce }`. On any failure, `text`
 * is null and `status`/`error` describe why.
 */
export async function fetchSitemap(url, {
  timeoutMs = DEFAULT_FETCH_TIMEOUT_MS,
  ua = BOT_UA,
  fetchImpl,
} = {}) {
  const _fetch = fetchImpl || globalThis.fetch;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await _fetch(url, {
      signal: controller.signal,
      headers: { 'User-Agent': ua, 'Accept': 'application/xml,text/xml,application/x-gzip,application/gzip,*/*' },
      redirect: 'follow',
    });
    if (!res.ok) {
      return {
        ok: false,
        status: res.status,
        text: null,
        error: null,
        isGz: false,
        ce: res.headers.get('content-encoding'),
        final: res.url,
      };
    }
    const ab = await res.arrayBuffer();
    const buf = Buffer.from(ab);
    const ce = (res.headers.get('content-encoding') || '').toLowerCase();
    const ct = (res.headers.get('content-type') || '').toLowerCase();
    const ceAlreadyDecoded = /gzip/i.test(ce);
    const urlSaysGz = /\.gz(\?|#|$)/i.test(url);
    const ctSaysGz = /gzip/i.test(ct);
    const magicSaysGz = (buf[0] === 0x1f && buf[1] === 0x8b);
    const isGz = !ceAlreadyDecoded && (urlSaysGz || ctSaysGz || magicSaysGz);
    let text;
    if (isGz) {
      try {
        text = gunzipSync(buf).toString('utf8');
      } catch (e) {
        return {
          ok: false,
          status: res.status,
          text: null,
          error: `gunzip: ${e.message}`,
          isGz: true,
          ce,
          final: res.url,
        };
      }
    } else {
      text = buf.toString('utf8');
    }
    return { ok: true, status: res.status, text, error: null, isGz, ce, final: res.url };
  } catch (e) {
    return {
      ok: false,
      status: 0,
      text: null,
      error: e?.message || String(e),
      isGz: false,
      ce: null,
      final: url,
    };
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Parse a sitemap XML string and extract the entries.
 * Returns `{ ok, isIndex, locs, error }`. `locs` is an array of strings.
 * The XML is intentionally permissive: a <parsererror> from xmldom
 * (malformed XML) is reported as `ok: false` but we don't try to
 * rescue the document with regex — sitemap authors either ship valid
 * XML or the sitemap is poison.
 */
export function parseSitemapXml(xml) {
  if (!xml || typeof xml !== 'string') {
    return { ok: false, isIndex: false, locs: [], error: 'empty_xml' };
  }
  try {
    const parser = new DOMParser();
    const doc = parser.parseFromString(xml, 'text/xml');
    const err = doc.getElementsByTagName('parsererror');
    if (err.length > 0) {
      return { ok: false, isIndex: false, locs: [], error: 'invalid_xml' };
    }
    const sitemapindex = doc.getElementsByTagName('sitemapindex');
    const isIndex = sitemapindex.length > 0;
    const urlset = doc.getElementsByTagName('urlset');
    const locs = [];
    if (isIndex) {
      const sitemaps = doc.getElementsByTagName('sitemap');
      for (let i = 0; i < sitemaps.length; i++) {
        const loc = sitemaps[i].getElementsByTagName('loc')[0];
        if (loc && loc.textContent) locs.push(loc.textContent.trim());
      }
    } else if (urlset.length > 0) {
      const allLocs = doc.getElementsByTagName('loc');
      for (let i = 0; i < allLocs.length; i++) {
        if (allLocs[i].textContent) locs.push(allLocs[i].textContent.trim());
      }
    } else {
      // No <sitemapindex> and no <urlset> — this could be a sitemap
      // listing locs directly (legacy format) or just garbage. Treat
      // it as a leaf with no locs rather than failing.
      return { ok: true, isIndex: false, locs: [], error: null, emptyShape: true };
    }
    return { ok: true, isIndex, locs, error: null };
  } catch (e) {
    return { ok: false, isIndex: false, locs: [], error: e.message || String(e) };
  }
}

/**
 * Recursively walk a sitemap URL and collect all product-shaped
 * <url><loc> entries across the whole sitemapindex tree. The caller
 * supplies a `productPattern` (RegExp or string) — only locs matching
 * it are counted. Non-matching locs are silently skipped (the live
 * retailer-sitemap-miner does the same).
 *
 * Returns `{ productUrls, subSitemapsWalked, errors, fetches }`.
 * `errors` is a list of `{ url, error }` so the worker can log per-URL
 * failure reasons without re-throwing. `fetches` is a count of HTTP
 * fetches performed (sitemapindex nodes + urlset leaves).
 */
export async function walkSitemapForProducts(sitemapUrl, {
  productPattern,
  ua = BOT_UA,
  timeoutMs = DEFAULT_FETCH_TIMEOUT_MS,
  maxDepth = DEFAULT_MAX_DEPTH,
  maxLocs = DEFAULT_MAX_LOCS,
  fetchImpl,
} = {}) {
  const productUrls = [];
  const errors = [];
  let subSitemapsWalked = 0;
  let fetches = 0;

  const pattern = productPattern instanceof RegExp
    ? productPattern
    : (productPattern ? new RegExp(productPattern, 'i') : null);

  // Internal: process a single sitemap URL at the given depth. Returns
  // a number of product URLs added. Uses iterative recursion via a
  // work-stack to avoid blowing the JS call stack on deep sitemapindex
  // trees (and to make the code easier to read than a recursive IIFE).
  const stack = [{ url: sitemapUrl, depth: 0 }];
  const seen = new Set();
  while (stack.length > 0) {
    if (productUrls.length >= maxLocs) break;
    const { url, depth } = stack.shift();
    if (seen.has(url)) continue;
    seen.add(url);
    if (depth > maxDepth) {
      errors.push({ url, error: 'max_depth' });
      continue;
    }
    fetches++;
    const res = await fetchSitemap(url, { timeoutMs, ua, fetchImpl });
    if (!res.ok) {
      errors.push({ url, error: res.error || `status_${res.status}` });
      continue;
    }
    const parsed = parseSitemapXml(res.text);
    if (!parsed.ok) {
      errors.push({ url, error: parsed.error });
      continue;
    }
    if (parsed.isIndex) {
      subSitemapsWalked++;
      for (const sub of parsed.locs) {
        if (productUrls.length >= maxLocs) break;
        stack.push({ url: sub, depth: depth + 1 });
      }
    } else {
      // urlset leaf — filter locs against the product pattern
      for (const loc of parsed.locs) {
        if (productUrls.length >= maxLocs) break;
        if (pattern && !pattern.test(loc)) continue;
        productUrls.push(loc);
      }
    }
  }

  return { productUrls, subSitemapsWalked, errors, fetches };
}

/**
 * Map a hostname to a 2-letter ISO country code. Covers the TLDs the
 * brand/retailer seed lists use. Generic TLDs (.com, .org, .net) and
 * ambiguous ccTLDs (.io, .ai, .co) fall through to 'US' — the
 * existing Shopify producer's COUNTRY_FILTER default is `US,SG` so
 * 'US' is a safe fallback that gets the new merchant re-enqueued for
 * scraping on the next cron tick. Operators can re-set the country
 * in the merchants table once a more specific value is known.
 */
export function countryFromHost(host) {
  if (!host || typeof host !== 'string') return 'US';
  const lower = host.toLowerCase();
  // Strip leading www. to avoid misclassifying 'www.co.uk' as 'uk'.
  const stripped = lower.replace(/^www\./, '');
  // Generic TLDs we never treat as country hints.
  const GENERIC_TLDS = new Set(['com', 'org', 'net', 'edu', 'gov', 'mil', 'int', 'biz', 'info', 'name', 'pro', 'aero', 'coop', 'museum']);
  // Two-part TLDs (.co.uk, .co.jp, .com.au) take priority.
  const twoPart = stripped.match(/\.([a-z]{2}\.[a-z]{2})$/);
  if (twoPart) {
    const tld = twoPart[1];
    if (tld === 'co.uk') return 'GB';
    if (tld === 'co.jp') return 'JP';
    if (tld === 'co.nz') return 'NZ';
    if (tld === 'co.za') return 'ZA';
    if (tld === 'com.au') return 'AU';
    if (tld === 'com.br') return 'BR';
    if (tld === 'com.mx') return 'MX';
    if (tld === 'com.sg') return 'SG';
  }
  // Single TLD.
  const single = stripped.match(/\.([a-z]{2,3})$/);
  if (single) {
    const tld = single[1];
    if (GENERIC_TLDS.has(tld)) return 'US';
    const TLD_TO_COUNTRY = {
      us: 'US', ca: 'CA', uk: 'GB', de: 'DE', fr: 'FR', it: 'IT', es: 'ES',
      nl: 'NL', se: 'SE', no: 'NO', dk: 'DK', fi: 'FI', pl: 'PL', at: 'AT',
      ch: 'CH', ie: 'IE', pt: 'PT', be: 'BE', jp: 'JP', au: 'AU', nz: 'NZ',
      sg: 'SG', hk: 'HK', kr: 'KR', in: 'IN', br: 'BR', mx: 'MX', za: 'ZA',
      ae: 'AE', sa: 'SA', il: 'IL', tr: 'TR', ru: 'RU', cn: 'CN', tw: 'TW',
    };
    if (TLD_TO_COUNTRY[tld]) return TLD_TO_COUNTRY[tld];
  }
  return 'US';
}

/**
 * Load a hand-curated seed list (brands or retailers) from a JSON file.
 * The shape is `{ entries: [{ domain, source, country, sitemaps, productPattern, uaMode }] }`.
 * Returns the array of entries. The file is intentionally a
 * hand-maintained JSON (not a JSONL like the WAT pool) so the brand
 * and retailer curators can review the file in one glance and add new
 * entries in one commit.
 */
export async function loadSeedList(filePath) {
  if (!filePath || typeof filePath !== 'string') {
    throw new Error('loadSeedList: filePath is required');
  }
  if (!existsSync(filePath)) {
    throw new Error(`loadSeedList: file not found: ${filePath}`);
  }
  let raw;
  try {
    raw = JSON.parse(readFileSync(filePath, 'utf8'));
  } catch (e) {
    throw new Error(`loadSeedList: invalid JSON in ${filePath}: ${e.message}`);
  }
  const entries = Array.isArray(raw) ? raw : (Array.isArray(raw.entries) ? raw.entries : null);
  if (!entries) {
    throw new Error(`loadSeedList: ${filePath} must be a JSON array or { entries: [...] }`);
  }
  return entries;
}

/**
 * Validate a single seed entry. Returns `{ ok, errors }` so the
 * producer can log a single-line error per malformed entry instead of
 * crashing the whole daily tick. Validation rules:
 *   - `domain` is a string with at least one dot.
 *   - `sitemaps` is a non-empty array of strings starting with http(s)://.
 *   - `productPattern` is a string (compiled to RegExp by the worker).
 *   - `source` is a string (used as the merchant.source label).
 *   - `country` is an optional string; falls back to countryFromHost(domain).
 *   - `uaMode` is an optional string in {'bot','desktop'}; defaults to 'bot'.
 */
export function validateSeedEntry(entry) {
  const errors = [];
  if (!entry || typeof entry !== 'object') {
    return { ok: false, errors: ['not_an_object'] };
  }
  if (!entry.domain || typeof entry.domain !== 'string' || !entry.domain.includes('.')) {
    errors.push('invalid_domain');
  }
  if (!Array.isArray(entry.sitemaps) || entry.sitemaps.length === 0) {
    errors.push('missing_sitemaps');
  } else {
    for (let i = 0; i < entry.sitemaps.length; i++) {
      const s = entry.sitemaps[i];
      if (typeof s !== 'string' || !/^https?:\/\//i.test(s)) {
        errors.push(`bad_sitemap[${i}]`);
      }
    }
  }
  if (!entry.productPattern || typeof entry.productPattern !== 'string') {
    errors.push('missing_productPattern');
  }
  if (!entry.source || typeof entry.source !== 'string') {
    errors.push('missing_source');
  }
  if (entry.uaMode && !['bot', 'desktop'].includes(entry.uaMode)) {
    errors.push('bad_uaMode');
  }
  return { ok: errors.length === 0, errors };
}

export const SUPPORTED_KINDS = ['brand', 'retailer'];
export const MIN_PRODUCTS_THRESHOLD = MIN_PRODUCT_URLS_TO_VERIFY;
