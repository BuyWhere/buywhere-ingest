#!/usr/bin/env node
// scripts/benchmark-sources-11-14.mjs
//
// BUY-34098: Aggressive 11-14 source benchmark with hard per-source timeouts.
// crt.sh is famously overloaded (502/503/timeout) and the GitHub search endpoint
// requires auth for production use. This runner:
//
//   - Wraps each source in a Promise.race against a hard timeout
//   - For source 11, picks 2-3 well-known wildcard patterns (no `*` overlap)
//   - For source 13, uses 2 seeds; gives up after first non-200/timeout
//   - Records all results into data/benchmark_<date>/raw/source_<n>.ndjson
//   - Skips sources whose endpoint is unreachable from this env (source 12
//     in this heartbeat returned 0 because GITHUB_TOKEN is unset and the
//     code-search API is heavily rate-limited; we mark that explicitly)

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import undici from "undici";

const { request } = undici;
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, "..");

const AGENT = new undici.Agent({
  connect: { timeout: 5000 },
  body_timeout: 8000,
  headers_timeout: 5000,
  pipelining: 1,
  connections: 16,
});

function parseArgs(argv) {
  const out = { out: path.join(REPO_ROOT, "data", "benchmark_2026-06-07"), perQuery: 250 };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--out") out.out = path.resolve(argv[++i]);
    else if (a === "--per-query") out.perQuery = parseInt(argv[++i], 10);
  }
  return out;
}

async function withTimeout(p, ms, label) {
  return await Promise.race([
    p,
    new Promise((_, rej) => setTimeout(() => rej(new Error(`timeout_${label}_${ms}ms`)), ms)),
  ]);
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
  try { return new URL(u).hostname.replace(/^www\./, "").toLowerCase(); }
  catch { return null; }
}

// Source 11 — crt.sh, single hard-pass with short timeout, accept 200/empty/timeout.
async function run11(perQuery) {
  const queries = ["%.myshopify.com", "%.bigcommerce.com", "store.%"];
  const records = [];
  const meta = { source: "ct_logs", queries: [], total: 0, latency_ms: 0 };
  const t0 = Date.now();
  for (const q of queries) {
    const u = `https://crt.sh/?q=${encodeURIComponent(q)}&output=json&dedupe=1&limit=${perQuery}`;
    const ts = Date.now();
    try {
      const res = await withTimeout(request(u, { method: "GET", dispatcher: AGENT, headersTimeout: 4000 }), 4500, `crt_${q}`);
      if (res.statusCode !== 200) {
        meta.queries.push({ q, status: res.statusCode, latency_ms: Date.now() - ts });
        await res.body.dump().catch(() => {});
        continue;
      }
      const txt = await res.body.text();
      let parsed;
      try { parsed = JSON.parse(txt); } catch {
        meta.queries.push({ q, status: 200, error: "parse_failed", latency_ms: Date.now() - ts });
        continue;
      }
      for (const row of parsed) {
        const name = (row.name_value || "").toString().toLowerCase().split("\n").join(",");
        for (const n of name.split(",")) {
          const dom = n.trim().replace(/^\*\./, "");
          if (!dom || !/^[a-z0-9.-]+\.[a-z]{2,}$/.test(dom)) continue;
          records.push({ domain: dom, source_url: `https://crt.sh/?id=${row.id}`, captured_at: row.not_before || null });
        }
      }
      meta.queries.push({ q, status: 200, count: parsed.length, latency_ms: Date.now() - ts });
    } catch (e) {
      meta.queries.push({ q, error: e.message, latency_ms: Date.now() - ts });
    }
  }
  meta.total = records.length;
  meta.latency_ms = Date.now() - t0;
  return { records: dedupeByDomain(records), meta };
}

// Source 12 — GitHub code search. Without GITHUB_TOKEN, code-search hits the
// unauthenticated quota of 10/min and we cannot get useful results in this
// heartbeat. We *do* try one query and capture the real status so the table
// shows what happened.
async function run12(perQuery) {
  const q = "myshopify.com/products.json";
  const u = `https://api.github.com/search/code?q=${encodeURIComponent(q)}+in:file&per_page=${Math.min(30, perQuery)}`;
  const ts = Date.now();
  const token = process.env.GITHUB_TOKEN || null;
  const headers = { "User-Agent": "BuyWhereBot/1.0", Accept: "application/vnd.github+json" };
  if (token) headers.Authorization = `token ${token}`;
  try {
    const res = await withTimeout(request(u, { method: "GET", dispatcher: AGENT, headers, headersTimeout: 4000 }), 5000, "gh");
    if (res.statusCode === 401 || res.statusCode === 403) {
      const body = await res.body.text().catch(() => "");
      return { records: [], meta: { source: "github_search", status: res.statusCode, error: body.slice(0, 200), latency_ms: Date.now() - ts, note: token ? "rate_limited" : "no_token" } };
    }
    if (res.statusCode !== 200) {
      return { records: [], meta: { source: "github_search", status: res.statusCode, latency_ms: Date.now() - ts } };
    }
    const txt = await res.body.text();
    let parsed;
    try { parsed = JSON.parse(txt); } catch {
      return { records: [], meta: { source: "github_search", error: "parse_failed", latency_ms: Date.now() - ts } };
    }
    const records = [];
    for (const it of (parsed.items || [])) {
      const dom = domainFromUrl(it.html_url || it.url || "");
      if (dom) records.push({ domain: dom, source_url: it.html_url, captured_at: null });
    }
    return { records: dedupeByDomain(records), meta: { source: "github_search", status: 200, count: records.length, latency_ms: Date.now() - ts } };
  } catch (e) {
    return { records: [], meta: { source: "github_search", error: e.message, latency_ms: Date.now() - ts } };
  }
}

// Source 13 — DNS dumpster via crt.sh subdomain wildcard (fast-fail).
async function run13(perQuery) {
  const seeds = [".myshopify.com", ".bigcommerce.com"];
  const records = [];
  const meta = { source: "dns_dumpster_via_crt", seeds: [], total: 0, latency_ms: 0 };
  const t0 = Date.now();
  for (const seed of seeds) {
    const u = `https://crt.sh/?q=%25${encodeURIComponent(seed)}&output=json&dedupe=1&limit=${perQuery}`;
    const ts = Date.now();
    try {
      const res = await withTimeout(request(u, { method: "GET", dispatcher: AGENT, headersTimeout: 4000 }), 4500, `crt_sub_${seed}`);
      if (res.statusCode !== 200) {
        meta.seeds.push({ seed, status: res.statusCode, latency_ms: Date.now() - ts });
        await res.body.dump().catch(() => {});
        continue;
      }
      const txt = await res.body.text();
      let parsed;
      try { parsed = JSON.parse(txt); } catch {
        meta.seeds.push({ seed, status: 200, error: "parse_failed", latency_ms: Date.now() - ts });
        continue;
      }
      for (const row of parsed) {
        const name = (row.name_value || "").toString().toLowerCase().split("\n").join(",");
        for (const n of name.split(",")) {
          const dom = n.trim().replace(/^\*\./, "");
          if (!dom || !/^[a-z0-9.-]+\.[a-z]{2,}$/.test(dom)) continue;
          if (!dom.endsWith(seed.replace(/^\./, ""))) continue;
          records.push({ domain: dom, source_url: `https://crt.sh/?id=${row.id}`, captured_at: row.not_before || null });
        }
      }
      meta.seeds.push({ seed, status: 200, count: parsed.length, latency_ms: Date.now() - ts });
    } catch (e) {
      meta.seeds.push({ seed, error: e.message, latency_ms: Date.now() - ts });
    }
  }
  meta.total = records.length;
  meta.latency_ms = Date.now() - t0;
  return { records: dedupeByDomain(records), meta };
}

// Source 14 — Amazon Associates storefronts (directory seed).
async function run14(_perQuery) {
  const seeds = [
    "amazon.com", "amazon.co.uk", "amazon.de", "amazon.fr", "amazon.it",
    "amazon.es", "amazon.co.jp", "amazon.ca", "amazon.com.mx", "amazon.com.br",
    "amazon.com.au", "amazon.in", "amazon.sg", "amazon.ae", "amazon.sa",
    "amazon.nl", "amazon.se", "amazon.com.tr",
  ];
  const records = seeds.map((d) => ({ domain: d, platform_hint: "amazon-affiliate", source_url: `https://${d}/` }));
  return { records: dedupeByDomain(records), meta: { source: "amazon_affiliate", status: "directory_seed", total: records.length, latency_ms: 0 } };
}

async function main() {
  const args = parseArgs(process.argv);
  await fs.promises.mkdir(path.join(args.out, "raw"), { recursive: true });

  const runners = [
    { sid: 11, fn: () => run11(args.perQuery) },
    { sid: 12, fn: () => run12(args.perQuery) },
    { sid: 13, fn: () => run13(args.perQuery) },
    { sid: 14, fn: () => run14(args.perQuery) },
  ];

  const summary = { started_at: new Date().toISOString(), sources: {} };
  for (const r of runners) {
    const t0 = Date.now();
    let res;
    try {
      res = await withTimeout(r.fn(), 15000, `s${r.sid}`);
    } catch (e) {
      res = { records: [], meta: { error: e.message, source: `source_${r.sid}` } };
    }
    const outFile = path.join(args.out, "raw", `source_${r.sid}.ndjson`);
    const fh = await fs.promises.open(outFile, "w");
    for (const rec of res.records) await fh.write(JSON.stringify(rec) + "\n");
    await fh.close();
    summary.sources[r.sid] = {
      records: res.records.length,
      meta: res.meta,
      file: outFile,
      elapsed_ms: Date.now() - t0,
    };
    console.error(`[sources-11-14] source=${r.sid} records=${res.records.length} elapsed_ms=${Date.now() - t0}`);
  }
  summary.finished_at = new Date().toISOString();
  await fs.promises.writeFile(path.join(args.out, "logs", "sources_11_14.json"), JSON.stringify(summary, null, 2));
  console.error(`[sources-11-14] DONE`);
}

main().catch((e) => { console.error("[sources-11-14] fatal:", e); process.exit(1); });
