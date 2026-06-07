// BUY-34838: Lane runner — page-1 fetch with role-specific quality filter.
//
// Mirrors the buy30620-page-lane-runner.mjs (5bc984ee-…) POOL_CONFIGS: five
// concurrent roles (hunt, hunt2, stock, crate, scout) with different
// concurrency / maxPages / qualityMode knobs. The original ran as a
// keep-alive loop writing NDJSON to disk; the new worker handler calls
// /v1/ingest/products directly so the drain loop is no longer needed.
//
// Quality modes:
//   - strict: rejects batches with no numeric price, > 50% placeholders,
//     or a single unique price + >= 85% blank images on >= 8 products.
//   - light:  same shape, but tolerates a higher imageNullShare (0.95)
//     and accepts batches with no numeric prices (the catalog will fill
//     them in from a later page).
//
// The fetcher hits /products.json?limit=250&page=N (the same path the
// live lane uses) instead of the sitemap walk, so a successful page-1
// returns up to 250 products in one round-trip. We use Node's built-in
// fetch + AbortController for the timeout.

const DEFAULT_TIMEOUT_MS = parseInt(process.env.LANE_FETCH_TIMEOUT_MS || '12000', 10);
const DEFAULT_MAX_RETRIES = parseInt(process.env.LANE_MAX_RETRIES || '3', 10);
const DEFAULT_RETRY_DELAY_MS = parseInt(process.env.LANE_RETRY_DELAY_MS || '750', 10);

export const LANE_ROLES = ['hunt', 'hunt2', 'stock', 'crate', 'scout'];

// Mirrors the original buy30620-page-lane-runner.mjs ROLE_CONFIGS. The
// worker reads these to populate per-role job payloads and to enforce
// the role-specific quality filter on the products the fetcher returns.
export const LANE_ROLE_CONFIG = {
  hunt: {
    defaultConcurrency: 6,
    qualityMode: 'light',
    maxPages: 40,
    pageDelayMs: 120,
    maxRetries: 4,
    retryDelayMs: 1200,
    fetchTimeoutMs: DEFAULT_TIMEOUT_MS,
    statusLabel: 'raw-feed-page-fallback',
  },
  hunt2: {
    defaultConcurrency: 6,
    qualityMode: 'light',
    maxPages: 40,
    pageDelayMs: 120,
    maxRetries: 4,
    retryDelayMs: 1200,
    fetchTimeoutMs: DEFAULT_TIMEOUT_MS,
    statusLabel: 'raw-feed-page-fallback',
  },
  stock: {
    defaultConcurrency: 6,
    qualityMode: 'light',
    maxPages: 40,
    pageDelayMs: 120,
    maxRetries: 4,
    retryDelayMs: 1200,
    fetchTimeoutMs: DEFAULT_TIMEOUT_MS,
    statusLabel: 'raw-feed-page-fallback',
  },
  crate: {
    defaultConcurrency: 4,
    qualityMode: 'strict',
    maxPages: 80,
    pageDelayMs: 250,
    maxRetries: 5,
    retryDelayMs: 1500,
    fetchTimeoutMs: DEFAULT_TIMEOUT_MS,
    statusLabel: 'deep-page-rate-limited',
  },
  scout: {
    defaultConcurrency: 8,
    qualityMode: 'strict',
    maxPages: 80,
    pageDelayMs: 100,
    maxRetries: 4,
    retryDelayMs: 1200,
    fetchTimeoutMs: 8000, // scout is a HEAD-style live validation; tighter timeout
    statusLabel: 'validate-fresh-feed',
  },
};

function normalizeDomain(value) {
  if (!value) return '';
  return String(value).trim().toLowerCase()
    .replace(/^https?:\/\//, '')
    .replace(/\/$/, '');
}

function parsePrice(value) {
  if (value == null) return null;
  const raw = String(value).replace(/[^0-9.\-]/g, '');
  const parsed = Number.parseFloat(raw);
  return Number.isFinite(parsed) ? parsed : null;
}

function extractImage(product) {
  return product?.image
    || product?.image_url
    || product?.featured_image
    || (Array.isArray(product?.images) && product.images[0] ? (product.images[0].src || null) : null);
}

function looksLikePlaceholderProduct(product) {
  const title = String(product?.title || '').toLowerCase().trim();
  if (!title || title.length < 4) return true;
  if (/^sample\b|\bplaceholder\b|\btest\b/i.test(title)) return true;
  const hasMeaningfulMeta = !!(product?.vendor || product?.product_type || product?.handle || product?.sku);
  if (!hasMeaningfulMeta) return true;
  const image = extractImage(product);
  if (image) return false;
  return ['test', 'demo', 'example'].some((token) => title.includes(token));
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchJsonPage(url, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, {
      signal: controller.signal,
      headers: {
        'User-Agent': 'Mozilla/5.0 BuyWhere-Lane/1.0',
        Accept: 'application/json',
      },
    });
    if (!res.ok) return { status: res.status, body: null, ok: false };
    const text = await res.text();
    let body = null;
    try { body = text ? JSON.parse(text) : null; } catch { return { status: res.status, body: null, ok: false }; }
    if (!body || !Array.isArray(body.products)) return { status: res.status, body: null, ok: false };
    return { status: res.status, body, ok: true };
  } catch {
    return { status: null, body: null, ok: false };
  } finally {
    clearTimeout(timer);
  }
}

export async function fetchLaneCandidatePages(domain, {
  maxPages = 40,
  pageDelayMs = 0,
  maxRetries = DEFAULT_MAX_RETRIES,
  retryDelayMs = DEFAULT_RETRY_DELAY_MS,
  fetchTimeoutMs = DEFAULT_TIMEOUT_MS,
  role = 'hunt',
} = {}) {
  const normalizedDomain = normalizeDomain(domain);
  if (!normalizedDomain) return null;
  const products = [];
  let status = null;
  let attempts = 0;
  const retryableStatuses = new Set([429, 500, 502, 503, 504, 404]);

  for (let page = 1; page <= maxPages; page++) {
    const url = `https://${normalizedDomain}/products.json?limit=250&page=${page}`;
    let response = null;
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      attempts += 1;
      response = await fetchJsonPage(url, fetchTimeoutMs);
      if (response.ok) break;
      if (!response.status || !retryableStatuses.has(response.status) || attempt >= maxRetries) break;
      await sleep(retryDelayMs * (2 ** attempt));
    }
    if (page === 1) {
      status = response?.status ?? null;
      if (status !== 200) {
        return { domain: normalizedDomain, status, products: [], pageCount: 0, attempts, role };
      }
    }
    if (!response?.body?.products || response.body.products.length === 0) break;

    for (const p of response.body.products) {
      const image = extractImage(p);
      const price = parsePrice(p.price || p.variants?.[0]?.price);
      products.push({
        id: String(p.id || ''),
        title: String(p.title || '').trim(),
        vendor: p.vendor || '',
        product_type: p.product_type || '',
        handle: p.handle || '',
        price,
        image: image ? String(image) : null,
        url: `https://${normalizedDomain}/products/${p.handle || ''}`,
        available: p.available ?? true,
      });
    }
    if (response.body.products.length < 250) break;
    if (pageDelayMs > 0 && page < maxPages) await sleep(pageDelayMs);
  }

  if (!products.length) return null;
  const firstPage = products[0];
  if (!firstPage.id || !firstPage.title) return null;

  const placeholderCount = products.filter(looksLikePlaceholderProduct).length;
  const placeholderRatio = placeholderCount / products.length;
  return {
    domain: normalizedDomain,
    status,
    products,
    pageCount: Math.ceil(products.length / 250),
    placeholderRatio,
    attempts,
    role,
  };
}

// Role-specific quality eval. Mirrors evaluateQuality() in
// scripts/lib/buy30620-discovery-common.mjs exactly so the worker
// accepts/rejects the same batches the live lane did.
export function evaluateLaneQuality(products, { mode = 'strict' } = {}) {
  const entries = (products || []).filter((p) => p && (p.title || p.id));
  if (!entries.length) return { pass: false, reason: 'no-products', metrics: {} };

  const prices = entries
    .map((e) => parsePrice(e.price))
    .filter((p) => typeof p === 'number' && Number.isFinite(p) && p > 0);

  if (!prices.length && mode === 'strict') {
    return { pass: false, reason: 'no-numeric-price', metrics: {} };
  }

  const uniquePriceCount = new Set(prices.map((p) => Number(p.toFixed(2)))).size;
  const imageNullCount = entries.filter((e) => !extractImage(e)).length;
  const imageNullShare = imageNullCount / entries.length;
  const placeholderCount = entries.filter(looksLikePlaceholderProduct).length;

  if (placeholderCount / entries.length > 0.5 && entries.length >= 6) {
    return {
      pass: false,
      reason: 'placeholder-like-product-ratio',
      metrics: { imageNullShare, uniquePriceCount, placeholderCount, productCount: entries.length },
    };
  }

  const suspiciousFlatPrice = (prices.length > 0 && uniquePriceCount === 1 && entries.length >= 8)
    || (mode !== 'strict' && prices.length === 0 && entries.length >= 8);
  const suspiciousImageBlank = imageNullShare >= (mode === 'strict' ? 0.85 : 0.95);
  if (suspiciousFlatPrice && suspiciousImageBlank) {
    return {
      pass: false,
      reason: 'likely-fabricated-batch',
      metrics: { imageNullShare, uniquePriceCount, placeholderCount, productCount: entries.length },
    };
  }

  return {
    pass: true,
    reason: 'ok',
    metrics: {
      imageNullShare: Number(imageNullShare.toFixed(4)),
      uniquePriceCount,
      numericPriceCount: prices.length,
      placeholderCount,
      productCount: entries.length,
    },
  };
}

// Convert a lane products[] into the buywhere-api /v1/ingest/products
// shape (sku/merchant_id/title/.../metadata). Same transform the live
// lane used when writing NDJSON, so the catalog row keys are stable
// across the cutover.
export function laneProductsToIngestRows(products, domain) {
  return products.map((p) => ({
    sku: `${domain}-${p.id}`,
    merchant_id: domain,
    title: p.title,
    description: '', // the JSON endpoint doesn't carry body_html; the api can re-scrape
    price: p.price == null ? 0 : p.price,
    currency: 'USD',
    url: p.url,
    image_url: p.image,
    brand: p.vendor || null,
    is_active: true,
    is_available: p.available !== false,
    metadata: {
      shopify_domain: domain,
      lane_role: p.role || null,
      scraped_at: new Date().toISOString(),
      handle: p.handle,
      product_type: p.product_type || null,
    },
  }));
}
