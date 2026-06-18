#!/usr/bin/env node
// scripts/deep-page-parallel.mjs
//
// BUY-32878: Parallel deep-pager for known e-commerce platforms.
// Input:  NDJSON from the prefilter (domain + platform + product_endpoint)
// Output: NDJSON of normalized product records (one per line)
//         Shape: { sku, source, merchant_id, title, description, price, currency,
//                  url, image_url, brand, category, category_path, is_active,
//                  in_stock, country_code, platform, scrape_transport }
//
// For now we deep-page Shopify (`/products.json?page=N&limit=250`) and
// Schema.org Product pages (crawl sitemap or product listings).
// WooCommerce/Magento/BigCommerce variants are emitted as platform-specific
// scraper calls — we will add a per-platform transport in a follow-up.

import fs from "node:fs";
import path from "node:path";
import zlib from "node:zlib";
import { fileURLToPath } from "node:url";
import undici from "undici";

const { request, Agent, interceptors } = undici;

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, "..");

const DISPATCHER = new Agent({
  connect: { timeout: 15000 },
  body_timeout: 30000,
  headers_timeout: 15000,
  pipelining: 1,
  connections: 200,
}).compose(interceptors.redirect({ maxRedirections: 3 }));

function parseArgs(argv) {
  const out = { input: null, output: null, concurrency: 50, perStoreMax: 500, merchantKey: "shopify" };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--input") out.input = argv[++i];
    else if (a === "--output") out.output = argv[++i];
    else if (a === "--concurrency") out.concurrency = parseInt(argv[++i], 10);
    else if (a === "--per-store-max") out.perStoreMax = parseInt(argv[++i], 10);
    else if (a === "--merchant-key") out.merchantKey = argv[++i];
  }
  return out;
}

async function readJSONL(file) {
  const txt = await fs.promises.readFile(file, "utf8");
  const out = [];
  for (const line of txt.split(/\r?\n/)) {
    if (!line.trim()) continue;
    try { out.push(JSON.parse(line)); } catch { /* skip */ }
  }
  return out;
}

async function getJSON(url, timeoutMs = 15000) {
  const start = Date.now();
  try {
    const res = await request(url, {
      method: "GET",
      dispatcher: DISPATCHER,
      headers: {
        "User-Agent": "Mozilla/5.0 (compatible; BuyWhereBot/1.0)",
        Accept: "application/json,text/html;q=0.9,*/*;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "en-US,en;q=0.5",
      },
      bodyTimeout: timeoutMs,
      headersTimeout: timeoutMs,
    });
    if (res.statusCode !== 200) {
      await res.body.dump().catch(() => {});
      return { ok: false, status: res.statusCode, latency_ms: Date.now() - start };
    }
    const enc = (res.headers["content-encoding"] || "").toLowerCase();
    let buf = Buffer.from(await res.body.arrayBuffer());
    if (enc === "gzip" || enc === "x-gzip") {
      buf = zlib.gunzipSync(buf);
    } else if (enc === "deflate") {
      buf = zlib.inflateSync(buf);
    } else if (enc === "br") {
      buf = zlib.brotliDecompressSync(buf);
    }
    const txt = buf.toString("utf8");
    return { ok: true, status: 200, body: txt, latency_ms: Date.now() - start };
  } catch (e) {
    return { ok: false, status: 0, error: e.message, latency_ms: Date.now() - start };
  }
}

function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }

function normalizeShopifyProduct(domain, p, merchantDefaults) {
  if (!p) return null;
  // Shopify stores vary: some use `handle`, some use `name` as the product key
  const handle = p.handle || p.slug || (typeof p.name === "string" ? p.name.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, "") : null);
  if (!handle) return null;
  const variant = (p.variants && p.variants[0]) || {};
  const image = (p.images && p.images[0] && p.images[0].src) || null;
  const price = variant.price ? String(variant.price) : (p.price ? String(p.price) : null);
  const currency = merchantDefaults.currency || "USD";
  const sku = variant.sku || variant.barcode || handle;
  const title = p.title || p.name || null;
  const description = (p.body_html || p.description || "").replace(/<[^>]+>/g, "").slice(0, 500);
  return {
    sku: `${domain}:${sku}`,
    source: merchantDefaults.source || `discovery_${domain.replace(/\./g, "_")}`,
    merchant_id: domain,
    title,
    description,
    price,
    currency,
    url: `https://${domain}/products/${handle}`,
    image_url: image,
    brand: p.vendor || null,
    category: p.product_type || null,
    category_path: p.product_type ? [p.product_type] : null,
    is_active: p.published_at ? true : false,
    in_stock: variant.available !== false,
    country_code: merchantDefaults.country_code || "US",
    platform: "shopify",
    scrape_transport: "products_json",
  };
}

async function deepPageShopify(domain, merchantDefaults, perStoreMax) {
  const products = [];
  const baseUrl = `https://${domain}`;
  let page = 1;
  const maxPages = Math.min(50, Math.ceil(perStoreMax / 250) + 5);
  let retries = 0;
  while (products.length < perStoreMax && page <= maxPages) {
    const url = `${baseUrl}/products.json?limit=250&page=${page}`;
    const r = await getJSON(url, 15000);
    process.stderr.write(`[dp] ${domain} page=${page} status=${r.status} bodyLen=${r.body?.length}\n`);
    if (!r.ok) {
      if (r.status === 429) {
        retries++;
        if (retries > 5) break;
        const backoff = Math.min(2000 * Math.pow(2, retries), 16000);
        await sleep(backoff);
        continue;
      }
      break;
    }
    retries = 0;
    let j;
    try { j = JSON.parse(r.body); } catch (e) { process.stderr.write(`[dp] ${domain} parse err: ${e.message}\n`); break; }
    if (!j.products || j.products.length === 0) {
      process.stderr.write(`[dp] ${domain} no products\n`);
      break;
    }
    for (const p of j.products) {
      const norm = normalizeShopifyProduct(domain, p, merchantDefaults);
      if (norm) products.push(norm);
      if (products.length >= perStoreMax) break;
    }
    if (j.products.length < 250) break;
    page++;
    await sleep(300);
  }
  return products;
}

function normalizeWooProduct(domain, p, merchantDefaults) {
  if (!p) return null;
  const price = (p.price != null) ? String(p.price) : (p.regular_price || null);
  const image = (p.images && p.images[0] && (p.images[0].src || p.images[0])) || null;
  const sku = p.sku || p.id || null;
  return {
    sku: `${domain}:${sku}`,
    source: merchantDefaults.source || `discovery_${domain.replace(/\./g, "_")}`,
    merchant_id: domain,
    title: p.name || null,
    description: (p.description || "").replace(/<[^>]+>/g, "").slice(0, 500),
    price: price != null ? String(price) : null,
    currency: merchantDefaults.currency || "USD",
    url: p.permalink || null,
    image_url: typeof image === "string" ? image : (image && image.src) || null,
    brand: p.brand || (p.categories && p.categories[0] && p.categories[0].name) || null,
    category: (p.categories && p.categories[0] && p.categories[0].name) || null,
    category_path: (p.categories || []).map((c) => c.name).filter(Boolean),
    is_active: p.status === "publish",
    in_stock: p.stock_status !== "outofstock",
    country_code: merchantDefaults.country_code || "US",
    platform: "woocommerce",
    scrape_transport: "wc_json",
  };
}

async function deepPageWoo(domain, merchantDefaults, perStoreMax) {
  const products = [];
  const baseUrl = `https://${domain}`;
  let page = 1;
  const maxPages = Math.min(50, Math.ceil(perStoreMax / 100) + 5);
  let retries = 0;
  while (products.length < perStoreMax && page <= maxPages) {
    const url = `${baseUrl}/wp-json/wc/v3/products?per_page=100&page=${page}`;
    const r = await getJSON(url, 15000);
    process.stderr.write(`[dp:wc] ${domain} page=${page} status=${r.status} bodyLen=${r.body?.length}\n`);
    if (!r.ok) {
      if (r.status === 429) {
        retries++;
        if (retries > 5) break;
        const backoff = Math.min(2000 * Math.pow(2, retries), 16000);
        await sleep(backoff);
        continue;
      }
      break;
    }
    retries = 0;
    let j;
    try { j = JSON.parse(r.body); } catch { break; }
    if (!Array.isArray(j) || j.length === 0) break;
    for (const p of j) {
      const norm = normalizeWooProduct(domain, p, merchantDefaults);
      if (norm) products.push(norm);
      if (products.length >= perStoreMax) break;
    }
    if (j.length < 100) break;
    page++;
    await sleep(300);
  }
  return products;
}

function normalizeMagentoProduct(domain, p, merchantDefaults) {
  if (!p || !p.sku) return null;
  const image = (p.media_gallery_entries && p.media_gallery_entries[0] && p.media_gallery_entries[0].file) || null;
  const price = (p.price != null) ? String(p.price) : null;
  return {
    sku: `${domain}:${p.sku}`,
    source: merchantDefaults.source || `discovery_${domain.replace(/\./g, "_")}`,
    merchant_id: domain,
    title: p.name || null,
    description: (p.description || p.short_description || "").replace(/<[^>]+>/g, "").slice(0, 500),
    price,
    currency: merchantDefaults.currency || "USD",
    url: p.extension_attributes && p.extension_attributes.url_key
      ? `https://${domain}/${p.extension_attributes.url_key}.html`
      : null,
    image_url: image ? `https://${domain}/media/catalog/product${image.startsWith("/") ? "" : "/"}${image}` : null,
    brand: p.brand || null,
    category: null,
    category_path: null,
    is_active: p.status === 1,
    in_stock: p.extension_attributes && p.extension_attributes.stock_item && p.extension_attributes.stock_item.qty > 0,
    country_code: merchantDefaults.country_code || "US",
    platform: "magento",
    scrape_transport: "rest_v1",
  };
}

async function deepPageMagento(domain, merchantDefaults, perStoreMax) {
  const products = [];
  const baseUrl = `https://${domain}`;
  let page = 1;
  const maxPages = Math.min(50, Math.ceil(perStoreMax / 100) + 5);
  let retries = 0;
  while (products.length < perStoreMax && page <= maxPages) {
    const url = `${baseUrl}/rest/V1/products?searchCriteria[pageSize]=100&searchCriteria[currentPage]=${page}`;
    const r = await getJSON(url, 15000);
    process.stderr.write(`[dp:mg] ${domain} page=${page} status=${r.status} bodyLen=${r.body?.length}\n`);
    if (!r.ok) {
      if (r.status === 429) {
        retries++;
        if (retries > 5) break;
        const backoff = Math.min(2000 * Math.pow(2, retries), 16000);
        await sleep(backoff);
        continue;
      }
      break;
    }
    retries = 0;
    let j;
    try { j = JSON.parse(r.body); } catch { break; }
    if (!j.items || j.items.length === 0) break;
    for (const p of j.items) {
      const norm = normalizeMagentoProduct(domain, p, merchantDefaults);
      if (norm) products.push(norm);
      if (products.length >= perStoreMax) break;
    }
    if (j.items.length < 100) break;
    page++;
    await sleep(300);
  }
  return products;
}

function normalizeBigCommerceProduct(domain, p, merchantDefaults) {
  if (!p || !p.id) return null;
  const image = (p.images && p.images[0] && (p.images[0].url_standard || p.images[0].url_zoom)) || null;
  return {
    sku: `${domain}:${p.sku || p.id}`,
    source: merchantDefaults.source || `discovery_${domain.replace(/\./g, "_")}`,
    merchant_id: domain,
    title: p.name || null,
    description: (p.description || "").replace(/<[^>]+>/g, "").slice(0, 500),
    price: p.price ? String(p.price) : null,
    currency: merchantDefaults.currency || "USD",
    url: (p.custom_url && p.custom_url.url) || `https://${domain}/products/${p.handle || p.id}/`,
    image_url: image,
    brand: p.brand || (p.categories && p.categories[0]) || null,
    category: (p.categories && p.categories[0]) || null,
    category_path: (p.categories || []).slice(0, 3),
    is_active: p.is_visible !== false,
    in_stock: p.inventory_level == null || p.inventory_level > 0,
    country_code: merchantDefaults.country_code || "US",
    platform: "bigcommerce",
    scrape_transport: "catalog_v3",
  };
}

async function deepPageBigCommerce(domain, merchantDefaults, perStoreMax) {
  const products = [];
  const baseUrl = `https://${domain}`;
  let page = 1;
  const maxPages = Math.min(50, Math.ceil(perStoreMax / 100) + 5);
  let retries = 0;
  while (products.length < perStoreMax && page <= maxPages) {
    const url = `${baseUrl}/api/catalog/products?limit=100&page=${page}`;
    const r = await getJSON(url, 15000);
    process.stderr.write(`[dp:bc] ${domain} page=${page} status=${r.status} bodyLen=${r.body?.length}\n`);
    if (!r.ok) {
      if (r.status === 429) {
        retries++;
        if (retries > 5) break;
        const backoff = Math.min(2000 * Math.pow(2, retries), 16000);
        await sleep(backoff);
        continue;
      }
      break;
    }
    retries = 0;
    let j;
    try { j = JSON.parse(r.body); } catch { break; }
    const items = Array.isArray(j) ? j : (j.data || []);
    if (items.length === 0) break;
    for (const p of items) {
      const norm = normalizeBigCommerceProduct(domain, p, merchantDefaults);
      if (norm) products.push(norm);
      if (products.length >= perStoreMax) break;
    }
    if (items.length < 100) break;
    page++;
    await sleep(300);
  }
  return products;
}

function extractSchemaProductsFromHtml(html, domain, merchantDefaults) {
  const products = [];
  const scriptRe = /<script[^>]+type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi;
  let m;
  while ((m = scriptRe.exec(html)) !== null) {
    let parsed;
    try { parsed = JSON.parse(m[1]); } catch { continue; }
    const items = Array.isArray(parsed) ? parsed : (parsed["@graph"] || [parsed]);
    for (const item of items) {
      if (!item || item["@type"] !== "Product") continue;
      const name = item.name || null;
      if (!name) continue;
      const offer = Array.isArray(item.offers) ? item.offers[0] : item.offers;
      const price = offer ? String(offer.price || offer.lowPrice || "") : null;
      const currency = (offer && offer.priceCurrency) || merchantDefaults.currency || "USD";
      const url = item.url || (offer && offer.url) || `https://${domain}/`;
      const image = Array.isArray(item.image) ? item.image[0] : (item.image || null);
      const imageUrl = typeof image === "object" && image ? image.url || null : (typeof image === "string" ? image : null);
      const sku = item.sku || item.productID || `${domain}:${name.toLowerCase().replace(/\s+/g, "-").slice(0, 60)}`;
      products.push({
        sku: `${domain}:${sku}`,
        source: merchantDefaults.source,
        merchant_id: domain,
        title: name,
        description: (typeof item.description === "string" ? item.description : "").slice(0, 500),
        price,
        currency,
        url,
        image_url: imageUrl,
        brand: (item.brand && (item.brand.name || item.brand)) || null,
        category: (item.category || null),
        category_path: item.category ? [item.category] : [],
        is_active: true,
        in_stock: !offer || offer.availability !== "https://schema.org/OutOfStock",
        country_code: merchantDefaults.country_code || "US",
        platform: "schema-product",
        scrape_transport: "schema_org",
      });
    }
  }
  return products;
}

async function deepPageSchemaProduct(domain, merchantDefaults, perStoreMax) {
  const products = [];
  // Try homepage first
  const home = await getJSON(`https://${domain}/`, 15000);
  if (home.ok && home.body) {
    const found = extractSchemaProductsFromHtml(home.body, domain, merchantDefaults);
    for (const p of found) { products.push(p); if (products.length >= perStoreMax) return products; }
  }
  // Try /sitemap.xml to find product pages
  if (products.length < perStoreMax) {
    const smap = await getJSON(`https://${domain}/sitemap.xml`, 10000);
    if (smap.ok && smap.body) {
      const urlRe = /<loc>(https?:\/\/[^<]+)<\/loc>/gi;
      const productUrls = [];
      let um;
      while ((um = urlRe.exec(smap.body)) !== null) {
        const u = um[1];
        if (/\/(product|item|shop|store|catalog|goods|p)\//i.test(u) || /\/products?\//i.test(u)) {
          productUrls.push(u);
        }
        if (productUrls.length >= 50) break;
      }
      for (const pu of productUrls) {
        if (products.length >= perStoreMax) break;
        const pg = await getJSON(pu, 12000);
        if (!pg.ok || !pg.body) continue;
        const found = extractSchemaProductsFromHtml(pg.body, domain, merchantDefaults);
        for (const p of found) { products.push(p); if (products.length >= perStoreMax) break; }
        await sleep(150);
      }
    }
  }
  return products;
}

function dispatchDeepPager(platform) {
  if (/^shopify/i.test(platform)) return deepPageShopify;
  if (/^woocommerce/i.test(platform)) return deepPageWoo;
  if (/^magento/i.test(platform)) return deepPageMagento;
  if (/^bigcommerce/i.test(platform)) return deepPageBigCommerce;
  if (/^schema/i.test(platform)) return deepPageSchemaProduct;
  return deepPageShopify;
}

async function main() {
  const args = parseArgs(process.argv);
  if (!args.input || !args.output) {
    console.error("Usage: deep-page-parallel.mjs --input filtered.ndjson --output products.ndjson [--concurrency 50] [--per-store-max 500] [--merchant-key shopify]");
    process.exit(2);
  }
  const records = await readJSONL(args.input);
  const ecomStores = records.filter((r) => typeof r.domain === "string" && r.platform && r.platform !== "unknown" && r.platform !== "error");
  const byPlatform = {};
  for (const r of ecomStores) byPlatform[r.platform] = (byPlatform[r.platform] || 0) + 1;
  console.error(`[deep-page] input records=${records.length} ecom=${ecomStores.length} by_platform=${JSON.stringify(byPlatform)} concurrency=${args.concurrency}`);

  const queue = [...ecomStores];
  const allProducts = [];
  const stats = { stores_processed: 0, stores_failed: 0, total_products: 0, by_platform: {}, started_at: new Date().toISOString() };

  async function worker(id) {
    while (queue.length) {
      const rec = queue.shift();
      if (!rec) return;
      const start = Date.now();
      const merchantDefaults = {
        source: `discovery_${rec.domain.replace(/[^a-z0-9]/gi, "_")}`,
        currency: rec.currency || "USD",
        country_code: rec.country_code || "US",
        platform: rec.platform || "shopify",
        region: "US",
      };
      const pager = dispatchDeepPager(rec.platform || "shopify");
      try {
        const products = await pager(rec.domain, merchantDefaults, args.perStoreMax);
        for (const p of products) allProducts.push(p);
        stats.stores_processed++;
        stats.total_products += products.length;
        stats.by_platform[rec.platform] = (stats.by_platform[rec.platform] || 0) + 1;
        if (stats.stores_processed % 25 === 0) {
          console.error(`[deep-page] worker=${id} stores=${stats.stores_processed} failed=${stats.stores_failed} products=${stats.total_products} by_platform=${JSON.stringify(stats.by_platform)}`);
        }
      } catch (e) {
        stats.stores_failed++;
      }
    }
  }

  const ws = [];
  for (let i = 0; i < args.concurrency; i++) ws.push(worker(i));
  await Promise.all(ws);

  await fs.promises.mkdir(path.dirname(args.output), { recursive: true });
  const fh = await fs.promises.open(args.output, "w");
  for (const p of allProducts) await fh.write(JSON.stringify(p) + "\n");
  await fh.close();

  stats.finished_at = new Date().toISOString();
  stats.output_rows = allProducts.length;
  console.error(`[deep-page] DONE: ${JSON.stringify(stats)}`);
}

main().catch((e) => {
  console.error("[deep-page] fatal:", e);
  process.exit(1);
});
