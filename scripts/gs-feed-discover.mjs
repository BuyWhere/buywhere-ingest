#!/usr/bin/env node
// scripts/gs-feed-discover.mjs
//
// BUY-9303: Discover working Google Shopping feed URLs for the ingestion pipeline.
//
// Strategy: For each confirmed merchant from the prefilter, probe a list of
// common public GS/XML feed paths. Validate by content-type and a small
// content sniff (XML/CSV-shaped, has product-shaped fields). Persist hits
// to NDJSON so the pipeline can ingest them.
//
// Common public feed locations (probed in this order):
//   1. /products.xml            (Shopify/WooCommerce/Adobe feed plugin default)
//   2. /feed/google.xml         (WooCommerce Google Product Feed plugin)
//   3. /google-shopping.xml
//   4. /googlebase.xml          (legacy WooCommerce extension)
//   5. /feed/googlebase.xml
//   6. /google-merchant-feed.xml
//   7. /google_product_feed.xml
//   8. /datafeed.xml
//   9. /feeds/google.xml
//  10. /products/google.xml
//  11. /exports/google.xml
//  12. /sitemap_products_1.xml  (Schema.org Product sitemap; same product data,
//                                parseable as a feed; last-resort fallback)
//
// Output: data/gs-feed-discovery/feeds_<timestamp>.ndjson

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import undici from "undici";

const { request, Agent, interceptors } = undici;

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, "..");

const DISPATCHER = new Agent({
  connect: { timeout: 8000 },
  body_timeout: 15000,
  headers_timeout: 8000,
  pipelining: 4,
  connections: 64,
}).compose(interceptors.redirect({ maxRedirections: 3 }));

const FEED_PATHS = [
  "products.xml",
  "feed/google.xml",
  "google-shopping.xml",
  "googlebase.xml",
  "feed/googlebase.xml",
  "google-merchant-feed.xml",
  "google_product_feed.xml",
  "datafeed.xml",
  "feeds/google.xml",
  "products/google.xml",
  "exports/google.xml",
];

// Last-resort sitemap fallback: not strictly a "feed" but the same product
// data, parseable, and widely deployed.
const SITEMAP_FALLBACK = "sitemap_products_1.xml";

const PRODUCT_HINTS = [
  "g:id",
  "<id>",
  "<title>",
  "<price",
  "<g:price",
  "<g:title",
  "<g:link",
  "<item>",
  "<product",
  "\"sku\"",
  "\"price\"",
  "\"title\"",
];

function ts() {
  return new Date().toISOString().replace(/[:.]/g, "-");
}

function pickUa() {
  return "Mozilla/5.0 (compatible; BuyWhereGSFeedProbe/1.0; +https://buywhere.ai/bot)";
}

async function probeUrl(rawUrl, timeoutMs = 12000) {
  const start = Date.now();
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await request(rawUrl, {
      method: "GET",
      dispatcher: DISPATCHER,
      signal: ctrl.signal,
      headers: {
        "user-agent": pickUa(),
        accept: "application/xml,text/xml,application/atom+xml,text/csv;q=0.9,*/*;q=0.8",
        "accept-encoding": "gzip, deflate, br",
      },
    });
    clearTimeout(timer);
    const status = res.statusCode;
    const ctype = (res.headers["content-type"] || "").toLowerCase();
    let body = "";
    try {
      // Cap to 256KB; just need a sniff
      const buf = await res.body.text({ limit: 256 * 1024 });
      body = buf || "";
    } catch {
      // ignore
    }
    return { status, ctype, body, elapsed_ms: Date.now() - start };
  } catch (e) {
    clearTimeout(timer);
    return { status: 0, ctype: "", body: "", error: e?.message || String(e), elapsed_ms: Date.now() - start };
  }
}

function looksLikeFeed(ctype, body) {
  if (!body) return { ok: false, reason: "empty" };
  // Hard size floor: real product feeds are at minimum a few KB
  if (body.length < 600) return { ok: false, reason: `too-small (${body.length}B)` };
  if (/(text\/csv|application\/csv|text\/plain)/.test(ctype)) {
    const head = body.slice(0, 4096).toLowerCase();
    if (/[,|\t].*[,|\t]/.test(head) && /(id|sku|title|name|price|product)/.test(head)) {
      return { ok: true, kind: "csv" };
    }
    return { ok: false, reason: "csv-but-no-product-headers" };
  }
  if (/(application\/xml|text\/xml|application\/atom\+xml|application\/rss\+xml)/.test(ctype) ||
      body.trimStart().startsWith("<?xml") || body.trimStart().startsWith("<rss") ||
      body.trimStart().startsWith("<feed") || body.trimStart().startsWith("<urlset")) {
    const head = body.slice(0, 16384).toLowerCase();
    const hits = PRODUCT_HINTS.filter((h) => head.includes(h));
    if (hits.length >= 2) return { ok: true, kind: "xml", hint: hits.join(",") };
    // sitemap is acceptable as a feed only if it has many product URLs
    if (head.includes("<urlset")) {
      const urlCount = (head.match(/<url>/g) || []).length;
      if (urlCount >= 5) return { ok: true, kind: "sitemap-products", hint: `${urlCount}-urls` };
      return { ok: false, reason: "sitemap-too-few-urls" };
    }
    return { ok: false, reason: "xml-but-no-product-shape" };
  }
  return { ok: false, reason: `not-xml-or-csv (${ctype || "no-ctype"})` };
}

async function probeDomain(domain, paths) {
  for (const p of paths) {
    const url = `https://${domain}/${p}`;
    const r = await probeUrl(url);
    if (r.status >= 200 && r.status < 300) {
      const verdict = looksLikeFeed(r.ctype, r.body);
      if (verdict.ok) {
        return { url, status: r.status, ctype: r.ctype, kind: verdict.kind, hint: verdict.hint || null, elapsed_ms: r.elapsed_ms, body_size: r.body.length };
      }
    } else if (r.status === 401 || r.status === 403) {
      // auth required - not useful for unauth pipeline
      continue;
    }
  }
  return null;
}

async function main() {
  const args = process.argv.slice(2);
  const inputIdx = args.indexOf("--input");
  const inputPath = inputIdx >= 0 ? args[inputIdx + 1] : "data/discovery_2026-06-06/prefilter_20k.ndjson";
  const outIdx = args.indexOf("--out");
  const ts_ = ts();
  const outDir = outIdx >= 0 ? args[outIdx + 1] : `data/gs-feed-discovery`;
  const outFile = path.join(outDir, `feeds_${ts_}.ndjson`);

  fs.mkdirSync(outDir, { recursive: true });

  if (!fs.existsSync(inputPath)) {
    console.error(`Input file not found: ${inputPath}`);
    process.exit(1);
  }

  const lines = fs.readFileSync(inputPath, "utf8").split(/\n/).filter(Boolean);
  const merchants = lines.map((l) => {
    try { return JSON.parse(l); } catch { return null; }
  }).filter((x) => x && x.domain);

  // Prioritize domains with confirmed platform endpoints - higher success rate
  const ranked = merchants.slice().sort((a, b) => {
    const score = (m) => (m.detection_method === "platform_endpoint" ? 2 : 1) + (m.platform === "shopify" ? 0.5 : 0);
    return score(b) - score(a);
  });

  const limitArg = args.indexOf("--limit");
  const limit = limitArg >= 0 ? parseInt(args[limitArg + 1], 10) : 50;
  const targets = ranked.slice(0, limit);

  console.log(`gs-feed-discover: probing ${targets.length}/${merchants.length} merchants from ${inputPath}`);
  console.log(`Platforms: ${JSON.stringify(targets.reduce((acc, m) => { acc[m.platform] = (acc[m.platform]||0)+1; return acc; }, {}))}`);

  const out = fs.createWriteStream(outFile, { flags: "w" });
  let hits = 0;
  let probed = 0;
  const startTotal = Date.now();
  const concurrency = 8;
  let cursor = 0;

  async function worker(id) {
    while (cursor < targets.length) {
      const myIdx = cursor++;
      const m = targets[myIdx];
      const paths = [...FEED_PATHS, SITEMAP_FALLBACK];
      const result = await probeDomain(m.domain, paths);
      probed++;
      if (result) {
        hits++;
        const record = {
          domain: m.domain,
          platform: m.platform,
          feed_url: result.url,
          feed_status: result.status,
          feed_content_type: result.ctype,
          feed_kind: result.kind,
          feed_hint: result.hint,
          body_size: result.body_size,
          elapsed_ms: result.elapsed_ms,
          country_code: m.country_code || null,
          probed_at: new Date().toISOString(),
        };
        out.write(JSON.stringify(record) + "\n");
        console.log(`[HIT ${id}] ${m.domain} (${m.platform}) -> ${result.url} [${result.kind}] status=${result.status} body=${result.body_size}B`);
      } else if ((probed % 10) === 0) {
        console.log(`[${id}] progress ${probed}/${targets.length} (${hits} hits so far) - last: ${m.domain}`);
      }
    }
  }

  await Promise.all(Array.from({ length: concurrency }, (_, i) => worker(i + 1)));
  out.end();
  const elapsed = ((Date.now() - startTotal) / 1000).toFixed(1);
  console.log(`\nDone. ${hits}/${probed} domains had a public GS-compatible feed (${elapsed}s)`);
  console.log(`Output: ${outFile}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
