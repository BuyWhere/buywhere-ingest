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
  if (!p || !p.handle) return null;
  const variant = (p.variants && p.variants[0]) || {};
  const image = (p.images && p.images[0] && p.images[0].src) || null;
  const price = variant.price ? String(variant.price) : null;
  const currency = merchantDefaults.currency || "USD";
  const sku = variant.sku || variant.barcode || p.handle;
  return {
    sku: `${domain}:${sku}`,
    source: merchantDefaults.source || `discovery_${domain.replace(/\./g, "_")}`,
    merchant_id: domain,
    title: p.title || null,
    description: (p.body_html || "").replace(/<[^>]+>/g, "").slice(0, 500),
    price: price,
    currency,
    url: `https://${domain}/products/${p.handle}`,
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

async function main() {
  const args = parseArgs(process.argv);
  if (!args.input || !args.output) {
    console.error("Usage: deep-page-parallel.mjs --input filtered.ndjson --output products.ndjson [--concurrency 50] [--per-store-max 500] [--merchant-key shopify]");
    process.exit(2);
  }
  const records = await readJSONL(args.input);
  const shopifyStores = records.filter((r) => typeof r.domain === "string" && /^shopify/i.test(r.platform || ""));
  console.error(`[deep-page] input records=${records.length} shopify=${shopifyStores.length} concurrency=${args.concurrency}`);

  const queue = [...shopifyStores];
  const allProducts = [];
  const stats = { stores_processed: 0, stores_failed: 0, total_products: 0, started_at: new Date().toISOString() };

  async function worker(id) {
    while (queue.length) {
      const rec = queue.shift();
      if (!rec) return;
      const start = Date.now();
      const merchantDefaults = {
        source: `discovery_${rec.domain.replace(/[^a-z0-9]/gi, "_")}`,
        currency: rec.currency || "USD",
        country_code: rec.country_code || "US",
        platform: "shopify",
        region: "US",
      };
      try {
        const products = await deepPageShopify(rec.domain, merchantDefaults, args.perStoreMax);
        for (const p of products) allProducts.push(p);
        stats.stores_processed++;
        stats.total_products += products.length;
        if (stats.stores_processed % 25 === 0) {
          console.error(`[deep-page] worker=${id} stores=${stats.stores_processed} failed=${stats.stores_failed} products=${stats.total_products}`);
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
