#!/usr/bin/env node
// scripts/gs-feed-cc-discover.mjs
//
// BUY-9303: Use CommonCrawl CDX to find historically advertised product feed URLs.
// CommonCrawl indexes the open web; merchants that once exposed /products.xml or
// similar on their site have left traces in CC's URL index. We can use those as
// candidates to re-validate, instead of probing blind.

import undici from "undici";
import fs from "node:fs";
import path from "node:path";

const { request } = undici;

const CC_CDX = "https://web.archive.org/cdx/search/cdx";
// Patterns merchants use to advertise a Google Shopping / product feed
const PATTERNS = [
  "products\\.xml",
  "feed/google",
  "googlebase\\.xml",
  "google-shopping",
  "google_product_feed",
  "datafeed\\.xml",
  "sitemap_products",
  "merchant.*feed",
];

function pickCdxIndex() {
  // Use a recent index
  return "CC-MAIN-2025-43";
}

async function ccSearch(pattern, limit = 500) {
  const url = `${CC_CDX}?url=*.com/${pattern}&output=json&limit=${limit}&fl=url,timestamp,status,mimetype&filter=statuscode:200&from=2024&to=2025`;
  try {
    const res = await request(url, {
      method: "GET",
      headers: { "user-agent": "BuyWhereGSFeedDiscovery/1.0" },
      headersTimeout: 30000,
      bodyTimeout: 60000,
    });
    if (res.statusCode !== 200) {
      console.error(`CC returned ${res.statusCode} for ${pattern}`);
      return [];
    }
    const text = await res.body.text();
    const rows = JSON.parse(text);
    if (!Array.isArray(rows) || rows.length < 2) return [];
    const header = rows[0];
    return rows.slice(1).map((r) => {
      const o = {};
      header.forEach((h, i) => (o[h] = r[i]));
      return o;
    });
  } catch (e) {
    console.error(`CC error for ${pattern}: ${e?.message || e}`);
    return [];
  }
}

async function main() {
  const ts = new Date().toISOString().replace(/[:.]/g, "-");
  const outDir = "data/gs-feed-discovery";
  fs.mkdirSync(outDir, { recursive: true });
  const outFile = path.join(outDir, `cc_candidates_${ts}.ndjson`);
  const out = fs.createWriteStream(outFile, { flags: "w" });

  console.log(`gs-feed-cc-discover: querying CommonCrawl CDX for ${PATTERNS.length} feed patterns`);
  let total = 0;
  const domainSet = new Set();

  for (const pat of PATTERNS) {
    console.log(`  pattern: ${pat}`);
    const hits = await ccSearch(pat, 200);
    console.log(`    -> ${hits.length} candidates`);
    for (const h of hits) {
      const rec = {
        pattern: pat,
        url: h.url,
        timestamp: h.timestamp,
        mimetype: h.mimetype,
        status: h.status,
        domain: (h.url || "").match(/^https?:\/\/([^/]+)/)?.[1] || null,
      };
      out.write(JSON.stringify(rec) + "\n");
      if (rec.domain) domainSet.add(rec.domain);
      total++;
    }
  }
  out.end();
  console.log(`\nDone. ${total} candidate URLs across ${domainSet.size} unique domains.`);
  console.log(`Output: ${outFile}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
