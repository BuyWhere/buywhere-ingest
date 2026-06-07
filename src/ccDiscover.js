// BUY-34835: Common Crawl Shopify discovery — strict-probe verifier + segment runner.
//
// Source scripts being migrated (and the rationale for this rewrite):
// - scripts/cc-shopify-index-loop.mjs + scripts/cc-shopify-index-expansion.mjs
//   (3ec8f6dd-…/scripts/) — Tranco-segment expansion, writes to JSONL files.
// - scripts/cc-shopify-discover-v2.mjs (5bc984ee-…/scripts/) — Tranco-based
//   Shopify probe at conc=3 with 8s timeout; lower hit rate than v16.
//
// The breakthrough this module is built on is the BUY-33160 v16 strict-probe
// pattern: conc=25, 20s timeout, retry x2 on fetch-failed, strict content-type
// (must be application/json + parsed {products:[...]} body) — that hit
// 60% verified on the 50k WAT pool (1,017 verified in early runs).
//
// We do NOT use the v16 script's WC store probe (that's for WooCommerce
// detection). For Shopify we hit /products.json?limit=1, which is what
// verifyShopifyViaHead() in cc-shopify-discover-v2.mjs already does — but we
// adopt the v16 retry/concurrency knobs, not v2's conc=3/8s.

// Shared with the wcDiscoverer/v2 scripts: a domain must have at least one
// dot and only URL-safe characters to be worth probing. Bare 'localhost' or
// 'foo' would pollute the merchants table.
export function isProbeableDomain(domain) {
  if (typeof domain !== 'string') return false;
  if (domain.length < 4 || domain.length > 253) return false;
  if (!domain.includes('.')) return false;
  if (/[\s/\\]/.test(domain)) return false;
  return true;
}

// Single strict probe — GET /products.json?limit=1, require 200 + JSON
// content-type + parseable {products:[...]} body. Returns one of:
//   { ok: true,  productsInCatalog, dt }
//   { ok: false, reason, dt }
// `reason` is short and stable so the worker can bucket it for stats.
export async function strictProbeShopifyOnce(domain, {
  timeoutMs = 20000,
  fetchImpl = globalThis.fetch,
} = {}) {
  const url = `https://${domain}/products.json?limit=1`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const t0 = Date.now();
  try {
    const res = await fetchImpl(url, {
      method: 'GET',
      signal: controller.signal,
      redirect: 'follow',
      headers: {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) {
      return { ok: false, reason: `HTTP ${res.status}`, dt: Date.now() - t0 };
    }
    const contentType = (res.headers.get('content-type') || '').toLowerCase();
    // Strict content-type: text/html means the site served a 404 page with
    // a 200 status (very common with catchall Shopify routes). Bail.
    if (!contentType.includes('application/json')) {
      return { ok: false, reason: `ct=${contentType.split(';')[0] || 'unknown'}`, dt: Date.now() - t0 };
    }
    const text = await res.text();
    if (text.length < 2) {
      return { ok: false, reason: 'empty_body', dt: Date.now() - t0 };
    }
    if (!text.includes('"products"')) {
      return { ok: false, reason: 'no_products_key', dt: Date.now() - t0 };
    }
    let body;
    try { body = JSON.parse(text); }
    catch { return { ok: false, reason: 'invalid_json', dt: Date.now() - t0 }; }
    if (!body || !Array.isArray(body.products)) {
      return { ok: false, reason: 'no_products_array', dt: Date.now() - t0 };
    }
    return { ok: true, productsInCatalog: body.products.length, dt: Date.now() - t0 };
  } catch (err) {
    const msg = String(err?.message || err || '').slice(0, 80);
    // undici surfaces transient network failures as "fetch failed" with a
    // cause chain — collapse to a single short reason for stats.
    const lower = msg.toLowerCase();
    let reason = 'fetch_failed';
    if (lower.includes('aborted') || lower.includes('abort')) reason = 'timeout';
    else if (lower.includes('enotfound')) reason = 'dns';
    else if (lower.includes('econn')) reason = 'connect';
    return { ok: false, reason, dt: Date.now() - t0, error: msg };
  } finally {
    clearTimeout(timer);
  }
}

// v16 retry: one retry on fetch-failed only (other failures are
// deterministic — retrying them just doubles the load).
export async function strictProbeShopify(domain, opts = {}) {
  const { retryDelayMs = 500, ...rest } = opts;
  let r = await strictProbeShopifyOnce(domain, rest);
  if (!r.ok && (r.reason === 'fetch_failed' || r.reason === 'timeout' || r.reason === 'connect')) {
    await new Promise((res) => setTimeout(res, retryDelayMs));
    r = await strictProbeShopifyOnce(domain, rest);
    if (r.ok) r.retried = true;
  }
  return r;
}

// Probe a list of domains with bounded concurrency. Returns a per-domain
// result map plus a stats summary. We intentionally do NOT throw on a bad
// probe — bad probes are the normal case (most domains in a WAT pool are
// dead). The caller decides what to do with each result.
export async function probeDomainsStrict(domains, {
  concurrency = 25,
  timeoutMs = 20000,
  retryDelayMs = 500,
  fetchImpl,
  onProgress,
} = {}) {
  const results = new Map();
  const stats = {
    probed: 0,
    verified: 0,
    dead: 0,
    retried: 0,
    errorMix: {},
    totalDtMs: 0,
    maxDtMs: 0,
  };

  // Snapshot the input — we mutate nothing.
  const list = Array.isArray(domains) ? domains.slice() : [];
  for (let i = 0; i < list.length; i += concurrency) {
    const slice = list.slice(i, i + concurrency);
    const settled = await Promise.allSettled(
      slice.map(async (d) => {
        const r = await strictProbeShopify(d, { timeoutMs, retryDelayMs, fetchImpl });
        return { domain: d, result: r };
      })
    );
    for (let k = 0; k < settled.length; k++) {
      const s = settled[k];
      stats.probed++;
      if (s.status !== 'fulfilled') {
        stats.dead++;
        const reason = 'promise_rejected';
        stats.errorMix[reason] = (stats.errorMix[reason] || 0) + 1;
        results.set(slice[k], { ok: false, reason, dt: 0 });
        continue;
      }
      const { domain, result } = s.value;
      results.set(domain, result);
      stats.totalDtMs += result.dt || 0;
      if ((result.dt || 0) > stats.maxDtMs) stats.maxDtMs = result.dt || 0;
      if (result.retried) stats.retried++;
      if (result.ok) {
        stats.verified++;
      } else {
        stats.dead++;
        const reason = result.reason || 'unknown';
        stats.errorMix[reason] = (stats.errorMix[reason] || 0) + 1;
      }
    }
    if (onProgress) {
      onProgress({
        done: Math.min(i + concurrency, list.length),
        total: list.length,
        verified: stats.verified,
        dead: stats.dead,
        retried: stats.retried,
      });
    }
  }
  return { results, stats };
}

// Load a candidate list from a path or a URL. The shape is the same as
// buy33160-v14-wat-pool.jsonl: one JSON object per line, each with at least
// `{domain, source}`. Comments (lines starting with '#') and malformed
// lines are skipped. Domain validity is enforced via isProbeableDomain.
export async function loadCandidateList(source) {
  // Lazy require so this module stays usable in unit tests where undici
  // isn't pulled in.
  const { readFileSync, existsSync } = await import('fs');
  let text;
  if (/^https?:\/\//i.test(source)) {
    const res = await fetch(source);
    if (!res.ok) {
      throw new Error(`loadCandidateList: HTTP ${res.status} fetching ${source}`);
    }
    text = await res.text();
  } else if (existsSync(source)) {
    text = readFileSync(source, 'utf-8');
  } else {
    throw new Error(`loadCandidateList: source not found: ${source}`);
  }
  const out = [];
  for (const line of text.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    try {
      const obj = JSON.parse(trimmed);
      if (obj && typeof obj.domain === 'string' && isProbeableDomain(obj.domain)) {
        out.push({
          domain: obj.domain.toLowerCase().replace(/^www\./, ''),
          source: typeof obj.source === 'string' ? obj.source : 'unknown',
        });
      }
    } catch {
      // skip malformed
    }
  }
  return out;
}
