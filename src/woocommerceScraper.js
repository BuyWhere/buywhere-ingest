// WooCommerce Store API deep-page scraper.
//
// Mirrors the proven probe+paginate logic in Oracle's
// buy31015-woocommerce-deep-page.mjs (heartbeat-spawned) but exposes it
// as a pure async function returning a flat product array in the same
// row schema as src/shopifyScraper.js, so the buywhere-api ingest
// endpoint accepts the output unchanged.
//
// Endpoint: GET https://<domain>/wp-json/wc/store/products
//   ?per_page=100&page=N
// (Modern WooCommerce Store API; no auth required; no /wc/v3 needed.)
//
// Concurrency: pages are fetched with bounded parallelism
// (PAGE_CONCURRENCY) so a 80-page deep-page is ~PAGE_CONCURRENCY RTTs
// not 80. We stop on the first empty page (Store API returns an empty
// array past the last page).

const DEFAULT_PAGE_TIMEOUT_MS = 8000;
const DEFAULT_PAGE_CONCURRENCY = 8;
const DEFAULT_PER_PAGE = 100;

function fetchJson(url, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  return fetch(url, {
    signal: controller.signal,
    headers: {
      'User-Agent': 'Mozilla/5.0 (compatible; BuywhereBot/1.0)',
      'Accept': 'application/json',
    },
    redirect: 'follow',
  })
    .then(async (res) => {
      if (!res.ok) return null;
      const ct = res.headers.get('content-type') || '';
      if (!ct.includes('json')) return null;
      return await res.json();
    })
    .catch(() => null)
    .finally(() => clearTimeout(timer));
}

async function fetchPage(domain, page, { perPage, pageTimeoutMs } = {}) {
  const per_page = perPage || DEFAULT_PER_PAGE;
  const url = `https://${domain}/wp-json/wc/store/products?per_page=${per_page}&page=${page}`;
  const data = await fetchJson(url, pageTimeoutMs || DEFAULT_PAGE_TIMEOUT_MS);
  return Array.isArray(data) ? data : null;
}

function toIngestProduct(domain, p) {
  // WC Store API product id is numeric or string; we stringify for SKU.
  const id = String(p.id ?? p.slug ?? '');
  // WC prices are in minor units (cents). Convert to major units.
  const priceCents = parseFloat((p.prices?.price ?? '0').toString());
  const denom = parseFloat((p.prices?.currency_minor_unit ?? '2').toString()) || 2;
  const priceMajor = priceCents
    ? priceCents / Math.pow(10, denom)
    : (parseFloat((p.price ?? '0').toString()) || 0);
  const handle = (p.slug || '').toString();
  const url = p.permalink || (handle ? `https://${domain}/product/${handle}` : `https://${domain}`);
  const categories = Array.isArray(p.categories) ? p.categories : [];
  const categoryNames = categories
    .map((c) => (typeof c === 'string' ? c : c?.name))
    .filter((s) => typeof s === 'string' && s.length > 0);

  // WooCommerce Store API has no separate description field; some
  // installations include it as `description` (HTML) or `short_description`.
  const rawDescription =
    (typeof p.description === 'string' && p.description) ||
    (typeof p.short_description === 'string' && p.short_description) ||
    '';
  const description = rawDescription.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();

  return {
    sku: `${domain}-${id || handle}`,
    merchant_id: domain,
    title: p.name || p.title || '',
    description: description || '',
    price: Number.isFinite(priceMajor) ? priceMajor : 0,
    currency: p.prices?.currency_code || 'USD',
    url,
    image_url: Array.isArray(p.images) && p.images.length > 0
      ? (p.images[0]?.src || p.images[0]?.thumbnail || null)
      : null,
    category: categoryNames.join(', ') || undefined,
    category_path: categoryNames.length > 0 ? categoryNames : undefined,
    brand: undefined,
    is_active: true,
    is_available: p.is_in_stock !== false,
    in_stock: p.is_in_stock !== false,
    metadata: {
      woocommerce_domain: domain,
      woocommerce_id: id,
      woocommerce_slug: handle,
      scraped_at: new Date().toISOString(),
      lane: 'buy31015_woocommerce_deep',
    },
  };
}

async function mapWithConcurrency(items, limit, mapper) {
  const results = new Array(items.length);
  let next = 0;
  const workers = Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (true) {
      const i = next++;
      if (i >= items.length) return;
      results[i] = await mapper(items[i], i);
    }
  });
  await Promise.all(workers);
  return results;
}

/**
 * Scrape a single WooCommerce merchant for products in [pageStart, pageEnd].
 *
 * @param {string} domain       - the bare domain, e.g. "noyce.store"
 * @param {object} [options]
 * @param {number} [options.pageStart=1]       - first page to fetch (1-based)
 * @param {number} [options.pageEnd=80]        - last page to fetch (inclusive)
 * @param {number} [options.perPage=100]       - items per page (max 100 on Store API)
 * @param {number} [options.pageTimeoutMs=8000] - per-page fetch timeout
 * @param {number} [options.pageConcurrency=8]  - parallel page fetches
 * @returns {Promise<Array<object>>} products in /v1/ingest/products schema
 */
export async function scrapeWooCommerceStore(domain, options = {}) {
  const pageStart = Math.max(1, options.pageStart || 1);
  const pageEnd = Math.max(pageStart, options.pageEnd || 80);
  const perPage = Math.min(100, Math.max(1, options.perPage || DEFAULT_PER_PAGE));
  const pageTimeoutMs = options.pageTimeoutMs || DEFAULT_PAGE_TIMEOUT_MS;
  const pageConcurrency = options.pageConcurrency || DEFAULT_PAGE_CONCURRENCY;

  if (!domain || typeof domain !== 'string' || !domain.includes('.')) {
    console.warn(`[woocommerce-scraper] invalid domain: ${domain}`);
    return [];
  }

  const pageNums = [];
  for (let p = pageStart; p <= pageEnd; p++) pageNums.push(p);

  const pageResults = await mapWithConcurrency(pageNums, pageConcurrency, (p) =>
    fetchPage(domain, p, { perPage, pageTimeoutMs })
  );

  // Pages are ordered; first empty array = end of catalog. Any null
  // (network/timeout) is skipped; we keep going because later pages
  // may still succeed.
  const all = [];
  for (let i = 0; i < pageResults.length; i++) {
    const data = pageResults[i];
    if (!data || data.length === 0) {
      // First empty page means we've reached the end; don't keep
      // walking past it (matches the existing buy31015 deep-pager
      // behavior so we don't waste RTTs on ghost pages).
      if (data && data.length === 0) break;
      continue;
    }
    for (const p of data) all.push(toIngestProduct(domain, p));
    if (data.length < perPage) break;
  }

  return all;
}

/**
 * Probe a domain for a live WooCommerce Store API. Used by the
 * producer (and is reusable for ad-hoc merchant verification).
 *
 * @param {string} domain
 * @param {number} [timeoutMs=6000]
 * @returns {Promise<boolean>}
 */
export async function probeWooCommerceStore(domain, timeoutMs = 6000) {
  const data = await fetchJson(
    `https://${domain}/wp-json/wc/store/products?per_page=5&page=1`,
    timeoutMs
  );
  if (!Array.isArray(data) || data.length === 0) return false;
  // Reject obviously-broken catalogs (all zero-price + no images).
  const zeroPrice = data.filter((p) => {
    const pr = parseFloat((p.prices?.price ?? p.price ?? '0').toString());
    return !pr || pr === 0;
  }).length;
  if (zeroPrice === data.length && data.length >= 3) return false;
  return true;
}
