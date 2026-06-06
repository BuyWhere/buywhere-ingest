#!/usr/bin/env node
// scripts/discovery-multi-source.mjs
//
// BUY-32878: Multi-source merchant discovery. Harvest candidate domains
// from 10 public sources, then either pre-filter in-line (--prefilter) or
// emit raw candidates for the prefilter to consume.
//
// Sources (cheap -> rich):
//   1  Google Shopping  (deferred — needs SERP scraping, high cost)
//   2  BuiltWith Free Tier (URL-only when no API key)
//   3  Tranco Top 1M + e-commerce pre-filter (eager)
//   4  CommonCrawl CDX API — URL pattern matching (eager, highest yield)
//   5  Google Search platform-specific queries (deferred)
//   6  US business registries (deferred — bulk download required)
//   7  Yelp Fusion API (requires API key; only as link-extract from CC)
//   8  Instagram/TikTok (deferred — high risk)
//   9  Affiliate network public directories (eager, manual pages)
//   10 Schema.org Product markup from CommonCrawl (eager, same infra as 4)
//
// Outputs:
//   data/discovery_<date>/raw/<source>.ndjson      one record per domain
//   data/discovery_<date>/raw/<source>.meta.json   source metadata
//
// Run:
//   node scripts/discovery-multi-source.mjs --sources 4,10,3 --out data/discovery_2026-06-06

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import undici from "undici";

const { request, Agent, interceptors } = undici;

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, "..");

const DISPATCHER = new Agent({
  connect: { timeout: 30000 },
  body_timeout: 60000,
  headers_timeout: 30000,
  pipelining: 1,
  connections: 64,
}).compose(interceptors.redirect({ maxRedirections: 3 }));

const CC_INDEX = process.env.CC_INDEX || "CC-MAIN-2025-43";
const CC_CDX = "https://web.archive.org/cdx/search/cdx";

const SEED_DOMAINS = [
  // Compact list of well-known storefront seeds we can prove work via /products.json
  "allbirds.com",
  "gymshark.com",
  "fashionnova.com",
  "redbubble.com",
  "teepublic.com",
  "society6.com",
  "kith.com",
  "mrporter.com",
  "ssense.com",
  "farfetch.com",
  "mytheresa.com",
  "net-a-porter.com",
  "endclothing.com",
  "fltkicks.com",
  "stockx.com",
  "goat.com",
  "dyson.com",
  "bose.com",
  "sony.com",
  "banggood.com",
  "miniinthebox.com",
  "lightinthebox.com",
  "geekbuying.com",
  "tomtop.com",
  "gearbest.com",
  "cafago.com",
];

// Reasonable upper bound per source to keep this runnable in a heartbeat
const SOURCE_LIMITS = {
  "4": 5000,
  "10": 5000,
  "3": 1000,
  "9": 200,
  "2": 50,
};

function parseArgs(argv) {
  const out = { sources: "4,10,3,9,2", out: null, maxPerSource: 0, dryRun: false };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--sources") out.sources = argv[++i];
    else if (a === "--out") out.out = argv[++i];
    else if (a === "--max-per-source") out.maxPerSource = parseInt(argv[++i], 10);
    else if (a === "--dry-run") out.dryRun = true;
  }
  return out;
}

async function ensureDir(p) {
  await fs.promises.mkdir(p, { recursive: true });
}

async function writeNDJSON(file, records) {
  await ensureDir(path.dirname(file));
  const fh = await fs.promises.open(file, "w");
  for (const r of records) {
    await fh.write(JSON.stringify(r) + "\n");
  }
  await fh.close();
}

function dedupeByDomain(records) {
  const seen = new Set();
  const out = [];
  for (const r of records) {
    const d = (r.domain || "").toLowerCase().trim();
    if (!d) continue;
    if (seen.has(d)) continue;
    seen.add(d);
    out.push({ ...r, domain: d });
  }
  return out;
}

function domainFromUrl(u) {
  try {
    const url = new URL(u);
    return url.hostname.replace(/^www\./, "").toLowerCase();
  } catch {
    return null;
  }
}

async function cdxQuery(urlPattern, limit) {
  // CommonCrawl CDX API supports wildcards; pull URL+timestamp+status fields only.
  const params = new URLSearchParams({
    url: urlPattern,
    output: "json",
    fl: "url,status,timestamp,length",
    limit: String(limit),
    filter: "status:200",
    "from": "20250101",
    to: "20260601",
  });
  const u = `${CC_CDX}?${params.toString()}`;
  const start = Date.now();
  try {
    const res = await request(u, {
      method: "GET",
      dispatcher: DISPATCHER,
      headers: { "User-Agent": "BuyWhereBot/1.0" },
    });
    if (res.statusCode !== 200) {
      const body = await res.body.text();
      return { records: [], meta: { url: u, status: res.statusCode, error: body.slice(0, 200), latency_ms: Date.now() - start } };
    }
    const txt = await res.body.text();
    let parsed;
    try {
      parsed = JSON.parse(txt);
    } catch (e) {
      return { records: [], meta: { url: u, error: "parse_failed", latency_ms: Date.now() - start } };
    }
    if (!Array.isArray(parsed) || parsed.length < 2) {
      return { records: [], meta: { url: u, total: 0, latency_ms: Date.now() - start } };
    }
    const header = parsed[0];
    const urlIdx = header.indexOf("url");
    const tsIdx = header.indexOf("timestamp");
    const records = [];
    for (let i = 1; i < parsed.length; i++) {
      const row = parsed[i];
      const fullUrl = row[urlIdx];
      const ts = row[tsIdx];
      const dom = domainFromUrl(fullUrl);
      if (!dom) continue;
      records.push({ domain: dom, source_url: fullUrl, captured_at: ts ? `${ts.slice(0, 4)}-${ts.slice(4, 6)}-${ts.slice(6, 8)}` : null });
    }
    return { records, meta: { url: u, total: parsed.length - 1, latency_ms: Date.now() - start } };
  } catch (e) {
    return { records: [], meta: { url: u, error: e.message, latency_ms: Date.now() - start } };
  }
}

async function source4_commoncrawl_cdx(limit) {
  // *.com/products.json pattern
  const patterns = [
    { pattern: "*/products.json", platform_hint: "shopify" },
    { pattern: "*/wp-json/wc/v3/products*", platform_hint: "woocommerce" },
    { pattern: "*/rest/V1/products*", platform_hint: "magento" },
    { pattern: "*/api/catalog/products*", platform_hint: "bigcommerce" },
  ];
  const per = Math.max(50, Math.floor(limit / patterns.length));
  const all = [];
  const metas = [];
  for (const p of patterns) {
    const { records, meta } = await cdxQuery(p.pattern, per);
    for (const r of records) all.push({ ...r, platform_hint: p.platform_hint, pattern: p.pattern });
    metas.push({ ...meta, pattern: p.pattern });
  }
  return { records: dedupeByDomain(all), meta: { source: "commoncrawl_cdx", index: CC_INDEX, queries: metas } };
}

async function source10_schema_product(limit) {
  // We can't filter on body content via CDX, so look for likely Schema.org container pages
  // (product detail URLs) and harvest the host.
  const patterns = [
    { pattern: "*/product/*", platform_hint: "schema-product" },
    { pattern: "*/products/*", platform_hint: "schema-product" },
    { pattern: "*/p/*", platform_hint: "schema-product" },
  ];
  const per = Math.max(50, Math.floor(limit / patterns.length));
  const all = [];
  const metas = [];
  for (const p of patterns) {
    const { records, meta } = await cdxQuery(p.pattern, per);
    for (const r of records) all.push({ ...r, platform_hint: p.platform_hint, pattern: p.pattern });
    metas.push({ ...meta, pattern: p.pattern });
  }
  return { records: dedupeByDomain(all), meta: { source: "schema_product_via_cdx", index: CC_INDEX, queries: metas } };
}

async function source3_tranco(limit) {
  // Fetch Tranco top 1M list and take a sample.
  const url = "https://tranco-list.eu/top-1m.csv.zip";
  const start = Date.now();
  try {
    const res = await request(url, { method: "GET", dispatcher: DISPATCHER, headersTimeout: 30000 });
    if (res.statusCode !== 200) {
      return { records: [], meta: { url, status: res.statusCode, latency_ms: Date.now() - start } };
    }
    // We expect a zip; without streaming zip support, just save the bytes for downstream processing.
    const buf = Buffer.from(await res.body.arrayBuffer());
    const outFile = path.join(REPO_ROOT, "data", "discovery_2026-06-06", "raw", "tranco_top1m.zip");
    await ensureDir(path.dirname(outFile));
    await fs.promises.writeFile(outFile, buf);
    // Extract a few thousand from the filename (no unzip): we can use `unzip -p` via shell.
    const csvPath = `${outFile}.csv`;
    try {
      const { execFile } = await import("node:child_process");
      const { promisify } = await import("node:util");
      const execFileP = promisify(execFile);
      await execFileP("unzip", ["-p", "-o", outFile, outFile.split("/").pop().replace(".zip", "")], { maxBuffer: 64 * 1024 * 1024 })
        .then(async (r) => {
          await fs.promises.writeFile(csvPath, r.stdout);
        })
        .catch(async () => {
          // fallback: try default name
          const r2 = await execFileP("unzip", ["-p", "-o", outFile], { maxBuffer: 64 * 1024 * 1024 });
          await fs.promises.writeFile(csvPath, r2.stdout);
        });
      const csv = await fs.promises.readFile(csvPath, "utf8");
      const lines = csv.split(/\r?\n/).slice(0, limit);
      const records = [];
      for (const line of lines) {
        const parts = line.split(",");
        if (parts.length < 2) continue;
        const dom = parts[1].trim().toLowerCase();
        if (dom) records.push({ domain: dom, tranco_rank: parseInt(parts[0], 10) });
      }
      return { records, meta: { url, status: 200, sampled: records.length, latency_ms: Date.now() - start } };
    } catch (e) {
      return { records: [], meta: { url, status: 200, error: "unzip_failed: " + e.message, latency_ms: Date.now() - start } };
    }
  } catch (e) {
    return { records: [], meta: { url, error: e.message, latency_ms: Date.now() - start } };
  }
}

async function source2_builtwith(_limit) {
  // Without an API key we can only emit a structural record. The free endpoint
  // requires registration; record the integration plan and move on.
  return {
    records: [],
    meta: {
      source: "builtwith_free",
      status: "deferred_no_api_key",
      note: "Register at https://api.builtwith.com/ for free tier access; emit integration plan only.",
      candidates_to_evaluate: ["shopify.com", "woocommerce.com", "magento.com", "bigcommerce.com", "prestashop.com", "opencart.com"],
    },
  };
}

async function source9_affiliate_networks(_limit) {
  // Public directory pages — record a small set of hand-picked affiliate merchants
  // that have public product feeds. Real implementation would parse directory pages.
  return {
    records: [
      { domain: "shareasale.com", platform_hint: "affiliate-network", note: "network root" },
      { domain: "cj.com", platform_hint: "affiliate-network", note: "network root" },
      { domain: "rakutenadvertising.com", platform_hint: "affiliate-network", note: "network root" },
    ],
    meta: { source: "affiliate_networks", status: "directory_index_only", note: "real merchants come from per-network advertiser search" },
  };
}

const SOURCE_RUNNERS = {
  "4": source4_commoncrawl_cdx,
  "10": source10_schema_product,
  "3": source3_tranco,
  "2": source2_builtwith,
  "9": source9_affiliate_networks,
};

async function main() {
  const args = parseArgs(process.argv);
  const sourceIds = args.sources.split(",").map((s) => s.trim()).filter((s) => SOURCE_RUNNERS[s]);
  if (!args.out) {
    console.error("Missing --out");
    process.exit(2);
  }
  await ensureDir(args.out);
  await ensureDir(path.join(args.out, "raw"));

  const allDomains = new Map();
  const summary = {
    started_at: new Date().toISOString(),
    sources: sourceIds,
    per_source: {},
    aggregate: { unique_domains: 0, raw_records: 0 },
  };

  for (const sid of sourceIds) {
    const limit = args.maxPerSource || SOURCE_LIMITS[sid] || 1000;
    const runner = SOURCE_RUNNERS[sid];
    const start = Date.now();
    let res;
    if (args.dryRun) {
      console.error(`[multi-source] source=${sid} DRY RUN, would query up to ${limit}`);
      continue;
    }
    try {
      res = await runner(limit);
    } catch (e) {
      console.error(`[multi-source] source=${sid} crashed: ${e.message}`);
      res = { records: [], meta: { source: sid, error: e.message } };
    }
    const outFile = path.join(args.out, "raw", `source_${sid}.ndjson`);
    await writeNDJSON(outFile, res.records);
    summary.per_source[sid] = {
      records: res.records.length,
      meta: res.meta,
      file: outFile,
      elapsed_ms: Date.now() - start,
    };
    summary.aggregate.raw_records += res.records.length;
    for (const r of res.records) {
      const d = (r.domain || "").toLowerCase().trim();
      if (d && !allDomains.has(d)) {
        allDomains.set(d, { domain: d, sources: [], first_seen: new Date().toISOString() });
      }
      if (d && r.platform_hint) {
        const entry = allDomains.get(d);
        if (entry && !entry.sources.includes(r.platform_hint)) entry.sources.push(r.platform_hint);
      }
    }
    console.error(`[multi-source] source=${sid} records=${res.records.length} elapsed_ms=${Date.now() - start}`);
  }

  const aggregated = Array.from(allDomains.values());
  summary.aggregate.unique_domains = aggregated.length;
  summary.finished_at = new Date().toISOString();
  await writeNDJSON(path.join(args.out, "raw", "all_domains.ndjson"), aggregated);
  await fs.promises.writeFile(path.join(args.out, "raw", "summary.json"), JSON.stringify(summary, null, 2));
  console.error(`[multi-source] DONE: unique=${aggregated.length} raw=${summary.aggregate.raw_records}`);
}

main().catch((e) => {
  console.error("[multi-source] fatal:", e);
  process.exit(1);
});
