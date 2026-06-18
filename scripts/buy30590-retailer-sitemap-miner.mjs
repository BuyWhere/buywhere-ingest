#!/usr/bin/env node
// scripts/buy30590-retailer-sitemap-miner.mjs
// BUY-30590: Retailer sitemap mining lane — discovers merchant sitemaps.

import { Agent } from "undici";
import { writeFileSync, mkdirSync } from "fs";
import { resolve } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = fileURLToPath(new URL(".", import.meta.url));
const ROOT = resolve(__dirname, "..");

const DISPATCHER = new Agent({ connections: 32, pipelining: 2 });

const DATA_DIR = resolve(ROOT, "data", "discovery_2026-06-06");
const RETAILER_SEEDS = [
  "target.com", "walmart.com", "homedepot.com", "lowes.com",
  "wayfair.com", "overstock.com", "macys.com", "nordstrom.com",
];

const SITEMAP_PATHS = ["/sitemap.xml", "/sitemap_index.xml", "/wp-sitemap.xml", "/sitemap/sitemap.xml"];

async function fetchSitemap(baseUrl) {
  for (const sp of SITEMAP_PATHS) {
    try {
      const u = `https://${baseUrl}${sp}`;
      const res = await fetch(u, { dispatcher: DISPATCHER, signal: AbortSignal.timeout(8000) });
      if (res.ok) return { url: u, status: res.status };
    } catch {}
  }
  return null;
}

async function extractDomainsFromSitemap(url) {
  try {
    const res = await fetch(url, { dispatcher: DISPATCHER, signal: AbortSignal.timeout(15000) });
    if (!res.ok) return [];
    const text = await res.text();
    const matches = [];
    const re = /https?:\/\/([a-z0-9.-]+\.[a-z]{2,})/gi;
    let m;
    while ((m = re.exec(text)) !== null) {
      const d = m[1].toLowerCase();
      if (d && !d.includes("google") && !d.includes("facebook")) matches.push(d);
    }
    return [...new Set(matches)];
  } catch {
    return [];
  }
}

let cycle = 0;
async function run() {
  console.error(`[retailer_sitemap_miner] cycle=${cycle} seeds=${RETAILER_SEEDS.length}`);
  const outFile = resolve(DATA_DIR, `retailer_sitemap_miner_cycle_${cycle}.json`);
  mkdirSync(resolve(DATA_DIR), { recursive: true });
  const domains = [];
  for (const seed of RETAILER_SEEDS) {
    const sitemap = await fetchSitemap(seed);
    if (sitemap) {
      const found = await extractDomainsFromSitemap(sitemap.url);
      domains.push(...found);
      console.error(`[retailer_sitemap_miner] seed=${seed} sitemap=${sitemap.url} domains=${found.length}`);
    }
  }
  const unique = [...new Set(domains)];
  writeFileSync(outFile, JSON.stringify({ cycle, domains: unique, count: unique.length }));
  console.error(`[retailer_sitemap_miner] cycle=${cycle} finished domains=${unique.length}`);
}

async function main() {
  console.error("[retailer_sitemap_miner] started");
  while (true) {
    await run();
    cycle++;
    await new Promise(r => setTimeout(r, 300000));
  }
}

main().catch(e => { console.error("[retailer_sitemap_miner] fatal:", e); process.exit(1); });
