#!/usr/bin/env node
// scripts/gs-feed-robots.mjs
//
// BUY-9303: Probe robots.txt for the targeted retailer list. Per Google policy
// any product feed declared in robots.txt is a public feed URL. Check
// `Sitemap: ...` and any /feed/* /products.* declarations.

import undici from "undici";
import fs from "node:fs";
import path from "node:path";

const { request, Agent, interceptors } = undici;

const DISPATCHER = new Agent({
  connect: { timeout: 8000 },
  body_timeout: 8000,
  headersTimeout: 8000,
  pipelining: 4,
  connections: 64,
}).compose(interceptors.redirect({ maxRedirections: 3 }));

const TARGETS = [
  "target.com", "walmart.com", "bestbuy.com", "homedepot.com", "lowes.com",
  "wayfair.com", "macys.com", "kohls.com", "nordstrom.com", "sephora.com",
  "ulta.com", "bhphotovideo.com", "newegg.com", "backcountry.com", "rei.com",
  "etsy.com", "argos.co.uk", "currys.co.uk", "johnlewis.com", "asos.com",
  "next.co.uk", "harrods.com", "bol.com", "otto.de", "mediamarkt.de",
  "jbhifi.com.au", "kogan.com", "lazada.sg", "shopee.sg", "fairprice.com.sg",
  "apple.com", "samsung.com", "sony.com", "lego.com", "ikea.com",
  "lululemon.com", "nike.com", "adidas.com", "hm.com", "zara.com",
  "uniqlo.com", "gap.com", "oldnavy.com", "anthropologie.com", "urbanoutfitters.com",
  "allbirds.com", "gymshark.com", "mrporter.com", "ssense.com", "farfetch.com",
];

const FEED_HINT = /(feed|product|sitemap.*product|\.xml|google-shopping|merchant|gpf)/i;

async function fetchRobots(domain) {
  try {
    const res = await request(`https://${domain}/robots.txt`, {
      method: "GET",
      dispatcher: DISPATCHER,
      headers: { "user-agent": "Mozilla/5.0 (compatible; BuyWhereGSFeedDiscovery/1.0)" },
    });
    if (res.statusCode !== 200) return { status: res.statusCode, lines: [], body: "" };
    const body = await res.body.text();
    return { status: 200, lines: body.split("\n"), body };
  } catch (e) {
    return { status: 0, lines: [], body: "", error: e?.message || String(e) };
  }
}

function extractFeedHints(body) {
  const matches = [];
  for (const line of body.split("\n")) {
    if (/^\s*(sitemap|disallow|allow)\s*:/i.test(line)) {
      const m = line.match(/^\s*(\w+)\s*:\s*(.*)/i);
      if (m) {
        const k = m[1].toLowerCase();
        const v = m[2].trim();
        if (k === "sitemap" || (k !== "disallow" && k !== "allow" && FEED_HINT.test(v))) {
          matches.push({ key: k, value: v });
        }
      }
    }
  }
  return matches;
}

async function main() {
  const ts = new Date().toISOString().replace(/[:.]/g, "-");
  const outDir = "data/gs-feed-discovery";
  fs.mkdirSync(outDir, { recursive: true });
  const outFile = path.join(outDir, `robots_hints_${ts}.ndjson`);
  const out = fs.createWriteStream(outFile, { flags: "w" });

  console.log(`gs-feed-robots: probing ${TARGETS.length} domains for robots.txt Sitemap/feed hints`);
  let withSitemap = 0;
  let withFeedHint = 0;
  let probed = 0;
  const start = Date.now();

  for (const d of TARGETS) {
    const r = await fetchRobots(d);
    probed++;
    let rec = {
      domain: d,
      status: r.status,
      body_size: r.body.length,
      hints: [],
    };
    if (r.status === 200) {
      const hints = extractFeedHints(r.body);
      rec.hints = hints;
      if (hints.some((h) => h.key === "sitemap")) withSitemap++;
      if (hints.some((h) => FEED_HINT.test(h.value) && /(feed|product|gpf|google|merchant)/.test(h.value))) withFeedHint++;
    }
    out.write(JSON.stringify(rec) + "\n");
    if (rec.hints.length > 0) {
      console.log(`[${d}] ${rec.hints.length} hints (sitemap=${rec.hints.filter((h) => h.key === "sitemap").length}, feed-ish=${rec.hints.filter((h) => /(feed|product|gpf|google|merchant)/.test(h.value)).length})`);
    } else if (probed % 10 === 0) {
      console.log(`[progress] probed=${probed} with_sitemap=${withSitemap} with_feed_hint=${withFeedHint} last=${d}`);
    }
  }
  out.end();
  const elapsed = ((Date.now() - start) / 1000).toFixed(1);
  console.log(`\nDone. ${probed} domains, ${withSitemap} had Sitemap: directives, ${withFeedHint} had feed-ish URLs. (${elapsed}s)`);
  console.log(`Output: ${outFile}`);
}

main().catch((e) => { console.error(e); process.exit(1); });
