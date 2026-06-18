#!/usr/bin/env node
// scripts/buy34098-benchmark-analyze.mjs
//
// BUY-34098: Analyze the 14-source benchmark output and produce the
// table Rich specified, plus ranking, hourly numbers, and top-3 verdicts.
//
// Usage: node scripts/buy34098-benchmark-analyze.mjs --in data/benchmark_2026-06-07 --hour-window 60

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, "..");

const SOURCES = [
  { id: 1, name: "Google Shopping", status: "deferred" },
  { id: 2, name: "BuiltWith Free Tier", status: "deferred" },
  { id: 3, name: "Tranco Top 1M + prefilter", status: "active" },
  { id: 4, name: "CommonCrawl CDX (URL patterns)", status: "active" },
  { id: 5, name: "Google Search platform queries", status: "deferred" },
  { id: 6, name: "US business registries", status: "deferred" },
  { id: 7, name: "Yelp Fusion", status: "deferred" },
  { id: 8, name: "Instagram/TikTok", status: "deferred" },
  { id: 9, name: "Affiliate network directories", status: "active" },
  { id: 10, name: "Schema.org Product from CommonCrawl", status: "active" },
  { id: 11, name: "CT logs (crt.sh)", status: "active" },
  { id: 12, name: "GitHub code search", status: "active" },
  { id: 13, name: "DNS Dumpster / subdomain enum", status: "active" },
  { id: 14, name: "Amazon Affiliate storefronts", status: "active" },
];

const DOMAIN_RE = /^[a-z0-9.-]+\.[a-z]{2,}$/;

function parseArgs(argv) {
  const out = { in: null, hourWindow: 60 };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--in") out.in = argv[++i];
    else if (a === "--hour-window") out.hourWindow = parseInt(argv[++i], 10);
  }
  return out;
}

function safeReadJSONL(p) {
  try {
    if (!fs.existsSync(p)) return [];
    const txt = fs.readFileSync(p, "utf8");
    const out = [];
    for (const line of txt.split(/\r?\n/)) {
      if (!line.trim()) continue;
      try { out.push(JSON.parse(line)); } catch { /* skip */ }
    }
    return out;
  } catch { return []; }
}

function safeReadJSON(p) {
  try {
    if (!fs.existsSync(p)) return null;
    return JSON.parse(fs.readFileSync(p, "utf8"));
  } catch { return null; }
}

function dedupeDomains(records) {
  const seen = new Set();
  const out = [];
  for (const r of records) {
    const d = (r.domain || "").toLowerCase().trim();
    if (!d || !DOMAIN_RE.test(d)) continue;
    if (seen.has(d)) continue;
    seen.add(d);
    out.push(r);
  }
  return out;
}

function fmtNum(n) {
  if (n == null) return "0";
  if (n >= 1e6) return (n / 1e6).toFixed(2) + "M";
  if (n >= 1e3) return (n / 1e3).toFixed(1) + "K";
  return String(n);
}

function fmtPct(n) {
  if (n == null) return "0%";
  return n.toFixed(2) + "%";
}

async function main() {
  const args = parseArgs(process.argv);
  if (!args.in) { console.error("--in required"); process.exit(2); }
  const baseDir = args.in;
  const rawDir = path.join(baseDir, "raw");
  const rawNewDir = path.join(baseDir, "raw_new");
  const prefilterDir = path.join(baseDir, "prefilter");
  const deepPageDir = path.join(baseDir, "deep-page");
  const logsDir = path.join(baseDir, "logs");

  const startedAt = safeReadText(path.join(baseDir, "started_at.txt"))?.trim() || null;
  const multiSummary = safeReadJSON(path.join(rawNewDir, "summary.json")) || safeReadJSON(path.join(rawDir, "summary.json")) || null;

  const perSource = {};
  for (const src of SOURCES) {
    const candidates = [];
    const files = [];
    for (const dir of [rawNewDir, rawDir]) {
      const f = path.join(dir, `source_${src.id}.ndjson`);
      if (fs.existsSync(f)) {
        const records = safeReadJSONL(f);
        candidates.push(...records);
        files.push(f);
      }
    }
    const deduped = dedupeDomains(candidates);
    perSource[src.id] = {
      ...src,
      files,
      domains_emitted: candidates.length,
      domains_unique: deduped.length,
      dedup_rate: candidates.length ? (1 - deduped.length / candidates.length) : 0,
    };
  }

  // Prefilter Tranco: count from 4 slice outputs (or tranco_50k.ndjson fallback)
  const prefilterOut = [];
  for (let i = 0; i < 4; i++) {
    const f = path.join(prefilterDir, `tranco_slice_${i}.ndjson`);
    if (fs.existsSync(f)) prefilterOut.push(...safeReadJSONL(f));
  }
  const prefilterTranco = path.join(prefilterDir, "tranco_50k.ndjson");
  if (fs.existsSync(prefilterTranco)) prefilterOut.push(...safeReadJSONL(prefilterTranco));
  const prefilterDeduped = dedupeDomains(prefilterOut);

  // Deep-page: count products ingested (any non-empty file)
  let deepPageProducts = 0;
  const dpCounts = {};
  if (fs.existsSync(deepPageDir)) {
    for (const f of fs.readdirSync(deepPageDir)) {
      if (!f.endsWith(".ndjson")) continue;
      const arr = safeReadJSONL(path.join(deepPageDir, f));
      let count = 0;
      for (const r of arr) {
        if (r.sku && r.merchant_id) count++;
      }
      deepPageProducts += count;
      dpCounts[f] = count;
    }
  }

  // Build the 14-source table.
  // "Domains Checked" = domains emitted by source
  // "Stores Found"   = unique stores that came back with a non-ecom "unknown" platform hit
  // "Products Ingested" = deep-page products traced back to source via domain overlap
  // "Hit Rate"       = (stores found / domains checked) %
  // "Time"           = wall-clock
  const sourceDomainSets = {};
  for (const id of Object.keys(perSource)) {
    sourceDomainSets[id] = new Set();
  }
  for (const id of Object.keys(perSource)) {
    for (const d of perSource[id].domains_emitted ? perSource[id].domains_unique || [] : []) {
      sourceDomainSets[id].add(d.domain);
    }
    // The dedup helper returns the records, not just domains. Use unique records.
    const records = perSource[id].domains_emitted
      ? dedupeDomains(
          perSource[id].files.flatMap((f) => safeReadJSONL(f))
        )
      : [];
    perSource[id]._unique_records = records;
    for (const r of records) sourceDomainSets[id].add(r.domain);
  }

  // Map deep-page products back to source by merchant_id.
  const allSourceDomains = new Set();
  for (const s of Object.values(sourceDomainSets)) for (const d of s) allSourceDomains.add(d);
  const productSourceMap = {};
  if (fs.existsSync(deepPageDir)) {
    for (const f of fs.readdirSync(deepPageDir)) {
      if (!f.endsWith(".ndjson")) continue;
      const arr = safeReadJSONL(path.join(deepPageDir, f));
      for (const p of arr) {
        if (!p.merchant_id) continue;
        for (const [id, set] of Object.entries(sourceDomainSets)) {
          if (set.has(p.merchant_id.toLowerCase())) {
            productSourceMap[id] = (productSourceMap[id] || 0) + 1;
          }
        }
      }
    }
  }

  // Multi-source summary meta provides per-source elapsed_ms
  const perSrcMeta = (multiSummary && multiSummary.per_source) || {};
  const rows = [];
  for (const src of SOURCES) {
    const ps = perSource[src.id];
    const meta = perSrcMeta[String(src.id)] || {};
    const domainsChecked = ps.domains_emitted || 0;
    const storesFound = ps.domains_unique || 0;
    const products = productSourceMap[src.id] || 0;
    const hitRate = domainsChecked > 0 ? (storesFound / domainsChecked) * 100 : 0;
    const wall = (meta && meta.elapsed_ms) ? (meta.elapsed_ms / 1000).toFixed(1) + "s" : "—";
    rows.push({
      ...src,
      domains_checked: domainsChecked,
      stores_found: storesFound,
      products_ingested: products,
      hit_rate_pct: hitRate,
      time: wall,
      status: ps.status || "active",
    });
  }

  // Apply ranking: drop <2% hit rate AND <1000 products/hr
  const hourlyFactor = 3600 / Math.max(1, args.hourWindow);
  const ranked = rows.map((r) => {
    const projectedProductsHr = r.products_ingested * hourlyFactor;
    const keep = (r.hit_rate_pct >= 2 || r.products_ingested === 0) && (projectedProductsHr >= 1000 || r.products_ingested === 0);
    return { ...r, projected_products_per_hr: projectedProductsHr, keep };
  });
  ranked.sort((a, b) => b.products_ingested - a.products_ingested);

  // Top-3
  const top3 = ranked.filter((r) => r.products_ingested > 0).slice(0, 3);
  const dropped = ranked.filter((r) => !r.keep);

  // Hourly throughput line.
  const now = new Date();
  const hh = String(now.getUTCHours()).padStart(2, "0");
  const mm = String(now.getUTCMinutes()).padStart(2, "0");
  const totalDomainsChecked = prefilterDeduped.length + rows.reduce((s, r) => s + r.domains_checked, 0);
  const totalStores = prefilterDeduped.length;
  const hourlyLine = `${hh}:${mm} | Domains: ${fmtNum(totalDomainsChecked)} | Candidates: ${fmtNum(prefilterOut.length)} | Stores: ${fmtNum(totalStores)} | Scraped: ${fmtNum(deepPageProducts)} | Ingested: ${fmtNum(deepPageProducts)} | Hit%: ${totalDomainsChecked ? fmtPct(totalStores / totalDomainsChecked * 100) : "0%"} | Rows/sec: ${fmtNum(deepPageProducts / Math.max(1, args.hourWindow * 3600))}`;

  // 14-source table (exact format)
  const table = ["Source | Domains Checked | Stores Found | Products Ingested | Hit Rate | Time"];
  for (const r of ranked) {
    table.push(`${r.id} ${r.name} | ${r.domains_checked} | ${r.stores_found} | ${r.products_ingested} | ${fmtPct(r.hit_rate_pct)} | ${r.time}`);
  }
  const tableOut = table.join("\n");

  // Write report
  const report = {
    generated_at: new Date().toISOString(),
    started_at: startedAt,
    hour_window_s: args.hourWindow * 3600,
    per_source: ranked,
    top_3: top3,
    dropped: dropped.map((d) => ({ id: d.id, name: d.name, hit_rate_pct: d.hit_rate_pct, products: d.products_ingested, reason: d.hit_rate_pct < 2 ? "low_hit_rate" : "low_throughput" })),
    totals: {
      prefilter_records: prefilterOut.length,
      prefilter_unique: prefilterDeduped.length,
      deep_page_products: deepPageProducts,
    },
    deep_page_files: dpCounts,
    hourly_line: hourlyLine,
    table_md: tableOut,
  };
  const reportPath = path.join(baseDir, "report.json");
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
  fs.writeFileSync(path.join(baseDir, "report_table.txt"), tableOut);
  fs.writeFileSync(path.join(baseDir, "report_hourly.txt"), hourlyLine);
  console.log(tableOut);
  console.log("\nHourly:", hourlyLine);
  console.log("\nTop-3:", top3.map((t) => `${t.id} ${t.name} (${t.products_ingested} products, ${fmtPct(t.hit_rate_pct)} hit)`).join(" | "));
  console.log("Dropped:", dropped.map((d) => `${d.id} ${d.name}`).join(", "));
  console.log("Report written:", reportPath);
}

function safeReadText(p) {
  try { return fs.readFileSync(p, "utf8"); } catch { return null; }
}

main().catch((e) => { console.error("[analyze] fatal:", e); process.exit(1); });
