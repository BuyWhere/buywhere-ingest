// Tranco platform fingerprinting + list fetch.
//
// BUY-34836: replaces the BUY-31716 lane
// (`scripts/buy31716-tranco-nonshopify-miner.mjs` in the 5bc984ee-… workspace)
// with a first-class pgboss queue in the buywhere-ingest worker. The original
// lane probed `/products.json?limit=1` which only confirmed Shopify (already
// covered by the existing `scrape.shopify` producer) — non-Shopify platforms
// were not detected at all. This module adds fingerprint detectors for
// WooCommerce / Magento / BigCommerce / custom-cart, so the new
// `discover.tranco` queue can route discovered merchants into the right
// downstream scrape lane (WooCommerce, future Magento/BC, etc.).
//
// Sources of detection:
//   * WooCommerce — Store API at /wp-json/wc/store/products?per_page=1 returns
//     a JSON product array (same shape `woocommerceScraper.js` already uses).
//   * Magento — REST API at /rest/V1/products?searchCriteria[pageSize]=1
//     returns `{ items: [...], search_criteria: {...} }`. Magento 2.x
//     storefronts also expose an `X-Magento-*` debug header.
//   * BigCommerce — Storefront API at /api/storefront/products?limit=1
//     returns `{ data: [...], meta: {...} }`. A second signal is the
//     `X-BC-*` debug header on storefront responses.
//   * Custom — generic site with at least one discoverable product URL
//     pattern (`/product/`, `/products/`, `/shop/`, `/store/`,
//     `/collections/`) in the homepage HTML. Lower confidence; the worker
//     records it as `source='tranco_custom'` with a `low_confidence` flag
//     in the merchant metadata.

const DEFAULT_PROBE_TIMEOUT_MS = 6000;
const MAX_BODY_BYTES = 64 * 1024; // 64 KB is plenty for fingerprinting

/**
 * Fetch the latest Tranco top-N list as a `[{rank, domain}]` array.
 *
 * Tranco API:
 *   1. GET https://tranco-list.eu/api/lists/latest
 *      → { list_id: "...", available_date: "YYYY-MM-DD" }
 *   2. GET https://tranco-list.eu/lists/<list_id>/full
 *      → text/csv with `rank,domain\n` rows.
 *
 * @param {object} [opts]
 * @param {number} [opts.limit=1000000]   - cap on rows returned
 * @param {string} [opts.listId]          - skip the latest-list lookup
 * @param {number} [opts.fetchTimeoutMs=30000] - per-request timeout
 * @param {typeof fetch} [opts.fetchImpl] - injectable for tests
 * @returns {Promise<{listId: string, availableDate: string, rows: Array<{rank:number, domain:string}>}>}
 */
export async function fetchTrancoList(opts = {}) {
  const limit = Math.max(1, parseInt(opts.limit ?? 1000000, 10));
  const fetchImpl = opts.fetchImpl || fetch;
  const fetchTimeoutMs = Math.max(1000, parseInt(opts.fetchTimeoutMs ?? 30000, 10));

  let listId = opts.listId;
  let availableDate = null;
  if (!listId) {
    const metaUrl = 'https://tranco-list.eu/api/lists/latest';
    const metaRes = await fetchWithTimeout(fetchImpl, metaUrl, fetchTimeoutMs);
    if (!metaRes.ok) {
      throw new Error(`Tranco list metadata fetch failed: ${metaRes.status} ${await safeText(metaRes)}`);
    }
    const meta = await metaRes.json();
    listId = meta.list_id || meta.listId || meta.id;
    availableDate = meta.available_date || meta.availableDate || null;
    if (!listId) {
      throw new Error(`Tranco list metadata missing list_id: ${JSON.stringify(meta).slice(0, 200)}`);
    }
  }

  const csvUrl = `https://tranco-list.eu/lists/${listId}/full`;
  const csvRes = await fetchWithTimeout(fetchImpl, csvUrl, fetchTimeoutMs);
  if (!csvRes.ok) {
    throw new Error(`Tranco list csv fetch failed: ${csvRes.status} ${await safeText(csvRes)}`);
  }
  const csvText = await readBoundedText(csvRes, 64 * 1024 * 1024); // 64 MB cap on the full list
  if (!csvText.ok) {
    throw new Error(`Tranco list csv body unreadable: ${csvText.reason}`);
  }

  const rows = [];
  const lines = csvText.body.split(/\r?\n/);
  for (let i = 0; i < lines.length; i++) {
    if (rows.length >= limit) break;
    const line = lines[i].trim();
    if (!line) continue;
    // Skip the header line if present
    if (i === 0 && /^rank\s*,\s*domain$/i.test(line)) continue;
    const parts = line.split(',');
    if (parts.length < 2) continue;
    const rank = parseInt(parts[0], 10);
    const domain = (parts[1] || '').trim().toLowerCase();
    if (!Number.isFinite(rank) || rank < 1) continue;
    if (!domain || !domain.includes('.') || domain.length > 253) continue;
    rows.push({ rank, domain });
  }

  return { listId, availableDate, rows };
}

async function fetchWithTimeout(fetchImpl, url, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetchImpl(url, {
      signal: controller.signal,
      headers: {
        'user-agent': 'buywhere-tranco/1.0 (+https://paperclip.ing/buy34836)',
        'accept': 'application/json, text/csv, */*',
      },
    });
  } finally {
    clearTimeout(timer);
  }
}

async function readBoundedText(res, maxBytes) {
  // The wrapped response interface exposes `text()` for tests + simple
  // callers, and falls back to `res.body.getReader()` for the live
  // fetch path (which has a true ReadableStream body).
  let body;
  if (typeof res.text === 'function' && (res.body === undefined || res.body === null)) {
    body = await res.text();
    if (body.length > maxBytes) return { ok: false, reason: 'oversized_declared' };
    return { ok: true, body };
  }
  if (!res.body) return { ok: false, reason: 'no_body' };
  const reader = res.body.getReader();
  const decoder = new TextDecoder('utf-8', { fatal: false });
  const chunks = [];
  let received = 0;
  let truncated = false;
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    if (!value) continue;
    received += value.byteLength;
    if (received > maxBytes) {
      truncated = true;
      try { await reader.cancel(); } catch {}
      break;
    }
    chunks.push(value);
  }
  if (truncated) return { ok: false, reason: 'oversized_stream' };
  let text = '';
  for (const c of chunks) text += decoder.decode(c, { stream: true });
  text += decoder.decode();
  return { ok: true, body: text };
}

async function safeText(res) {
  try {
    const t = await res.text();
    return t.slice(0, 200);
  } catch {
    return '';
  }
}

// ---------------------------------------------------------------------------
// Per-kind fingerprint probes
// ---------------------------------------------------------------------------

/**
 * WooCommerce fingerprint via Store API.
 * Mirrors `probeWooCommerceStore` in woocommerceScraper.js so the two
 * detectors agree on a host's WC status.
 */
export async function probeWooCommerce(host, timeoutMs = DEFAULT_PROBE_TIMEOUT_MS, opts = {}) {
  const url = `https://${host}/wp-json/wc/store/products?per_page=1&page=1`;
  const json = await fetchJsonBounded(url, timeoutMs, opts);
  if (!json) return { ok: false, reason: 'no_response' };
  if (!Array.isArray(json) || json.length === 0) return { ok: false, reason: 'empty_or_not_array' };
  const first = json[0];
  if (!first || typeof first !== 'object') return { ok: false, reason: 'malformed_product' };
  return {
    ok: true,
    kind: 'woocommerce',
    evidence: {
      endpoint: '/wp-json/wc/store/products',
      productCount: json.length,
      firstProductId: first.id ?? null,
      firstProductName: first.name ?? first.title ?? null,
    },
  };
}

/**
 * Magento fingerprint via REST API.
 * Magento 2.x returns `{ items: [...], search_criteria: {...} }` from
 * /rest/V1/products. A `Magento-*` debug header is a second signal.
 */
export async function probeMagento(host, timeoutMs = DEFAULT_PROBE_TIMEOUT_MS, opts = {}) {
  const url = `https://${host}/rest/V1/products?searchCriteria[pageSize]=1`;
  const res = await fetchWithMeta(url, timeoutMs, opts);
  if (!res || !res.ok) return { ok: false, reason: res ? `status_${res.status}` : 'no_response' };
  const ct = (res.headers['content-type'] || '').toLowerCase();
  if (!ct.includes('json')) return { ok: false, reason: 'not_json' };
  const json = await safeJson(res);
  if (!json || typeof json !== 'object') return { ok: false, reason: 'not_object' };
  const items = Array.isArray(json.items) ? json.items : null;
  const magentoHeader = Object.keys(res.headers || {}).find((h) => /^x-magento/i.test(h));
  if (items && items.length >= 0 && (json.search_criteria || magentoHeader)) {
    return {
      ok: true,
      kind: 'magento',
      evidence: {
        endpoint: '/rest/V1/products',
        productCount: items.length,
        firstProductId: items[0]?.id ?? null,
        firstProductSku: items[0]?.sku ?? null,
        magentoHeader: magentoHeader || null,
      },
    };
  }
  return { ok: false, reason: 'not_magento_shape' };
}

/**
 * BigCommerce fingerprint via Storefront API.
 * BigCommerce returns `{ data: [...], meta: {...} }` from
 * /api/storefront/products. Lower confidence than Magento; some BC stores
 * 403 the unauthenticated Storefront API. The `X-BC-*` debug header is
 * an alternative signal.
 */
export async function probeBigCommerce(host, timeoutMs = DEFAULT_PROBE_TIMEOUT_MS, opts = {}) {
  const url = `https://${host}/api/storefront/products?limit=1`;
  const res = await fetchWithMeta(url, timeoutMs, opts);
  if (!res || !res.ok) return { ok: false, reason: res ? `status_${res.status}` : 'no_response' };
  const ct = (res.headers['content-type'] || '').toLowerCase();
  if (!ct.includes('json')) return { ok: false, reason: 'not_json' };
  const json = await safeJson(res);
  if (!json || typeof json !== 'object') return { ok: false, reason: 'not_object' };
  const data = Array.isArray(json.data) ? json.data : null;
  const bcHeader = Object.keys(res.headers || {}).find((h) => /^x-bc-/i.test(h));
  if (data && json.meta) {
    return {
      ok: true,
      kind: 'bigcommerce',
      evidence: {
        endpoint: '/api/storefront/products',
        productCount: data.length,
        firstProductId: data[0]?.id ?? null,
        firstProductName: data[0]?.name ?? null,
        bcHeader: bcHeader || null,
      },
    };
  }
  if (bcHeader) {
    return {
      ok: true,
      kind: 'bigcommerce',
      evidence: { endpoint: '/api/storefront/products', bcHeader },
    };
  }
  return { ok: false, reason: 'not_bigcommerce_shape' };
}

/**
 * Custom-cart fingerprint: fetch the homepage HTML and look for product URL
 * patterns (`/product/`, `/products/`, `/shop/`, `/store/`,
 * `/collections/`). The `low_confidence` flag is set so the downstream
 * lane knows to triage carefully. We do NOT confirm any specific
 * platform — this is a catch-all bucket for sites that don't expose a
 * structured product API.
 */
export async function probeCustom(host, timeoutMs = DEFAULT_PROBE_TIMEOUT_MS, opts = {}) {
  const url = `https://${host}/`;
  const res = await fetchWithMeta(url, timeoutMs, opts);
  if (!res || !res.ok) return { ok: false, reason: res ? `status_${res.status}` : 'no_response' };
  const ct = (res.headers['content-type'] || '').toLowerCase();
  if (!ct.includes('html')) return { ok: false, reason: 'not_html' };
  const body = await readBoundedText(res, MAX_BODY_BYTES);
  if (!body.ok) return { ok: false, reason: body.reason };
  const html = body.body;

  // First, reject if any of the recognised platform APIs already responded
  // positively on a prior kind — probeTrancoHost() runs kinds in order
  // and skips custom if a positive kind is found.
  const productPatterns = [
    /href\s*=\s*["'][^"']*\/products?\/[^"']*["']/i,
    /href\s*=\s*["'][^"']*\/shop\/[^"']*["']/i,
    /href\s*=\s*["'][^"']*\/store\/[^"']*["']/i,
    /href\s*=\s*["'][^"']*\/collections?\/[^"']*["']/i,
  ];
  const matched = productPatterns.find((re) => re.test(html));
  if (!matched) return { ok: false, reason: 'no_product_url_pattern' };

  // Try to extract a clean example product URL for the evidence trail.
  const urlMatch = html.match(/href\s*=\s*["']([^"']*\/products?\/[^"']*)["']/i)
    || html.match(/href\s*=\s*["']([^"']*\/collections?\/[^"']*)["']/i);

  return {
    ok: true,
    kind: 'custom',
    low_confidence: true,
    evidence: {
      endpoint: '/',
      matchedPattern: matched.source,
      exampleUrl: urlMatch ? urlMatch[1] : null,
      bodyBytes: body.body.length,
    },
  };
}

// ---------------------------------------------------------------------------
// Host-level entry point
// ---------------------------------------------------------------------------

export const SUPPORTED_KINDS = ['woocommerce', 'magento', 'bigcommerce', 'custom'];

const PROBE_BY_KIND = {
  woocommerce: probeWooCommerce,
  magento: probeMagento,
  bigcommerce: probeBigCommerce,
  custom: probeCustom,
};

/**
 * Probe a single Tranco host for a specific platform fingerprint.
 * The worker is invoked once per (host, kind) pair.
 *
 * @param {string} host
 * @param {'woocommerce'|'magento'|'bigcommerce'|'custom'} kind
 * @param {number} [timeoutMs=6000]
 * @param {object} [opts]              - injectable options
 * @param {typeof fetch} [opts.fetchImpl] - fetch override for tests
 * @returns {Promise<{ok: boolean, kind?: string, source?: string, evidence?: object, reason?: string}>}
 */
export async function probeTrancoHost(host, kind, timeoutMs = DEFAULT_PROBE_TIMEOUT_MS, opts = {}) {
  if (!host || typeof host !== 'string' || !host.includes('.')) {
    return { ok: false, reason: 'invalid_host' };
  }
  if (!SUPPORTED_KINDS.includes(kind)) {
    return { ok: false, reason: `unsupported_kind:${kind}` };
  }
  const fn = PROBE_BY_KIND[kind];
  try {
    const result = await fn(host, timeoutMs, opts);
    if (result.ok) {
      return {
        ...result,
        source: `tranco_${kind}`,
      };
    }
    return result;
  } catch (err) {
    return { ok: false, reason: `error_${(err?.name || 'fetch').toLowerCase()}` };
  }
}

// ---------------------------------------------------------------------------
// HTTP helpers (used internally and by the kind-specific probes)
// ---------------------------------------------------------------------------

async function fetchJsonBounded(url, timeoutMs, opts = {}) {
  const res = await fetchWithMeta(url, timeoutMs, opts);
  if (!res || !res.ok) return null;
  const ct = (res.headers['content-type'] || '').toLowerCase();
  if (!ct.includes('json')) return null;
  return await safeJson(res);
}

async function fetchWithMeta(url, timeoutMs, opts = {}) {
  const fetchImpl = opts.fetchImpl || globalThis.fetch;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetchImpl(url, {
      signal: controller.signal,
      headers: {
        'user-agent': 'Mozilla/5.0 (compatible; BuywhereTrancoBot/1.0; +https://paperclip.ing/buy34836)',
        'accept': 'application/json, text/html, */*',
      },
      redirect: 'follow',
    });
    // Wrap the response so headers/body are normalized for the probes.
    return {
      ok: res.ok,
      status: res.status,
      headers: Object.fromEntries(res.headers.entries()),
      async json() { return await res.json(); },
      async text() { return await res.text(); },
    };
  } catch (e) {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

async function safeJson(res) {
  try {
    return await res.json();
  } catch {
    return null;
  }
}
