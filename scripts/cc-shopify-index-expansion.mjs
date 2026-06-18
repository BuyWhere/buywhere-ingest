#!/usr/bin/env node
// scripts/cc-shopify-index-expansion.mjs
// Shopify index expansion lane — grows shopify merchant index via CC CDX and domain probes.

import { Agent } from "undici";
import { writeFileSync, mkdirSync } from "fs";
import { resolve } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = fileURLToPath(new URL(".", import.meta.url));
const ROOT = resolve(__dirname, "..");

const DISPATCHER = new Agent({ connections: 48, pipelining: 4 });

const CC_CDX = "https://web.archive.org/cdx/search/cdx";
const CC_INDEX = "CC-MAIN-2025-43";
const DATA_DIR = resolve(ROOT, "data", "discovery_2026-06-06");
const CRAWL_LIMIT = 500;

async function cdxQuery(pattern) {
  const params = new URLSearchParams({
    url: pattern,
    output: "json",
    fl: "url",
    limit: String(CRAWL_LIMIT),
    filter: "status:200",
    from: "20250101",
    to: "20260601",
  });
  try {
    const res = await fetch(`${CC_CDX}?${params}`, { dispatcher: DISPATCHER, signal: AbortSignal.timeout(20000) });
    if (!res.ok) return [];
    const txt = await res.text();
    const parsed = JSON.parse(txt);
    if (!Array.isArray(parsed) || parsed.length < 2) return [];
    const urlIdx = parsed[0].indexOf("url");
    const domains = [];
    for (let i = 1; i < parsed.length; i++) {
      const url = parsed[i][urlIdx];
      try {
        const u = new URL(url);
        const d = u.hostname.replace(/^www\./, "").toLowerCase();
        if (d) domains.push(d);
      } catch {}
    }
    return [...new Set(domains)];
  } catch {
    return [];
  }
}

async function probeShopify(domain) {
  try {
    const res = await fetch(`https://${domain}/products.json?limit=1`, {
      dispatcher: DISPATCHER,
      signal: AbortSignal.timeout(5000),
      headers: { "User-Agent": "BuyWhereBot/1.0" },
    });
    if (res.ok) {
      const j = await res.json();
      if (Array.isArray(j.products)) return { domain, platform: "shopify", ok: true };
    }
    return { domain, ok: false };
  } catch {
    return { domain, ok: false };
  }
}

const PATTERNS = [
  "*/products.json",
  "*/shopify/*",
];

let cycle = 0;
async function run() {
  console.error(`[shopify_index_expansion] cycle=${cycle} patterns=${PATTERNS.length}`);
  mkdirSync(resolve(DATA_DIR), { recursive: true });
  const allDomains = [];
  for (const p of PATTERNS) {
    const found = await cdxQuery(p);
    console.error(`[shopify_index_expansion] pattern=${p} found=${found.length}`);
    allDomains.push(...found);
  }
  const unique = [...new Set(allDomains)];
  const outFile = resolve(DATA_DIR, `shopify_index_expansion_cycle_${cycle}.json`);
  writeFileSync(outFile, JSON.stringify({ cycle, domains: unique, count: unique.length }));
  console.error(`[shopify_index_expansion] cycle=${cycle} finished domains=${unique.length}`);
}

async function main() {
  console.error("[shopify_index_expansion] started");
  while (true) {
    await run();
    cycle++;
    await new Promise(r => setTimeout(r, 300000));
  }
}

main().catch(e => { console.error("[shopify_index_expansion] fatal:", e); process.exit(1); });
