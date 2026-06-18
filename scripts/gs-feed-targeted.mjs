#!/usr/bin/env node
// scripts/gs-feed-targeted.mjs
//
// BUY-9303: Quick targeted probe of known major retailers for public Google Shopping
// feed endpoints. Larger retailers are more likely to have product feeds (the
// GS Product Feed plugin or equivalents are common on enterprise stores).

import undici from "undici";
import fs from "node:fs";
import path from "node:path";

const { request, Agent, interceptors } = undici;

const DISPATCHER = new Agent({
  connect: { timeout: 8000 },
  body_timeout: 12000,
  headers_timeout: 8000,
  pipelining: 4,
  connections: 64,
}).compose(interceptors.redirect({ maxRedirections: 3 }));

const TARGETS = [
  // Major US retailers
  "target.com", "walmart.com", "bestbuy.com", "homedepot.com", "lowes.com",
  "wayfair.com", "staples.com", "officedepot.com", "macys.com", "kohls.com",
  "jcpenney.com", "nordstrom.com", "sephora.com", "ulta.com", "bhphotovideo.com",
  "newegg.com", "adorama.com", "backcountry.com", "rei.com", "dickssportinggoods.com",
  "etsy.com", "ebay.com", "shopify.com",
  // UK / EU
  "argos.co.uk", "currys.co.uk", "johnlewis.com", "asos.com", "next.co.uk",
  "selfridges.com", "harrods.com", "debenhams.com", "marksandspencer.com",
  "bol.com", "otto.de", "mediamarkt.de", "saturn.de", "conrad.de",
  // AU
  "jbhifi.com.au", "kogan.com", "catch.com.au", "bigw.com.au", "target.com.au",
  // SG / SEA (in scope for BuyWhere)
  "lazada.sg", "shopee.sg", "qoo10.sg", "redmart.sg", "fairprice.com.sg",
  "courts.com.sg", "harveynorman.com.sg", "gaincity.com", "challenger.sg",
  "apple.com/sg", "samsung.com/sg", "sony.com.sg",
  // CA
  "canadiantire.ca", "walmart.ca", "bestbuy.ca", "thebay.com", "londondrugs.com",
  // India
  "flipkart.com", "myntra.com", "snapdeal.com", "croma.com", "reliance digital",
  "tatacliq.com", "nykaa.com", "ajio.com",
];

const FEED_PATHS = [
  "products.xml", "feed/google.xml", "googlebase.xml", "google-shopping.xml",
  "google_product_feed.xml", "datafeed.xml", "feed/google", "feeds/google.xml",
  "sitemap_products_1.xml", "products/google.xml", "exports/google.xml",
];

const PRODUCT_HINTS = ["g:id", "<id>", "<title>", "<price", "<g:price", "<g:title", "<g:link", "<item>", "<product"];

async function probeUrl(rawUrl) {
  try {
    const res = await request(rawUrl, {
      method: "GET",
      dispatcher: DISPATCHER,
      headers: {
        "user-agent": "Mozilla/5.0 (compatible; BuyWhereGSFeedProbe/1.0)",
        accept: "application/xml,text/xml,application/atom+xml,text/csv;q=0.9,*/*;q=0.8",
        "accept-encoding": "gzip, deflate, br",
      },
    });
    const ctype = (res.headers["content-type"] || "").toLowerCase();
    let body = "";
    try { body = await res.body.text({ limit: 256 * 1024 }); } catch {}
    return { status: res.statusCode, ctype, body };
  } catch (e) {
    return { status: 0, ctype: "", body: "", error: e?.message || String(e) };
  }
}

function isValidFeed(ctype, body) {
  if (!body || body.length < 600) return null;
  if (/(application\/xml|text\/xml|application\/atom\+xml|application\/rss\+xml)/.test(ctype) ||
      /^<\?xml|^<rss|^<feed|^<urlset/i.test(body.trimStart())) {
    const head = body.slice(0, 16384).toLowerCase();
    const hits = PRODUCT_HINTS.filter((h) => head.includes(h));
    if (hits.length >= 2) return { kind: "xml", hits };
    if (head.includes("<urlset")) {
      const urlCount = (head.match(/<url>/g) || []).length;
      if (urlCount >= 5) return { kind: "sitemap-products", hits: [`${urlCount}-urls`] };
    }
  }
  return null;
}

async function main() {
  const ts = new Date().toISOString().replace(/[:.]/g, "-");
  const outDir = "data/gs-feed-discovery";
  fs.mkdirSync(outDir, { recursive: true });
  const outFile = path.join(outDir, `targeted_feeds_${ts}.ndjson`);
  const out = fs.createWriteStream(outFile, { flags: "w" });

  console.log(`gs-feed-targeted: probing ${TARGETS.length} known major retailers for ${FEED_PATHS.length} feed paths`);
  let hits = 0;
  let probed = 0;
  const start = Date.now();

  for (const d of TARGETS) {
    let foundForDomain = null;
    for (const p of FEED_PATHS) {
      const url = `https://${d}/${p}`;
      const r = await probeUrl(url);
      probed++;
      if (r.status >= 200 && r.status < 300) {
        const verdict = isValidFeed(r.ctype, r.body);
        if (verdict) {
          hits++;
          foundForDomain = { url, status: r.status, ctype: r.ctype, kind: verdict.kind, hits: verdict.hits, body_size: r.body.length };
          break;
        }
      }
    }
    if (foundForDomain) {
      const rec = {
        domain: d,
        feed_url: foundForDomain.url,
        status: foundForDomain.status,
        content_type: foundForDomain.ctype,
        feed_kind: foundForDomain.kind,
        product_hints: foundForDomain.hits,
        body_size: foundForDomain.body_size,
        probed_at: new Date().toISOString(),
      };
      out.write(JSON.stringify(rec) + "\n");
      console.log(`[HIT] ${d} -> ${foundForDomain.url} [${foundForDomain.kind}] ${foundForDomain.body_size}B`);
    } else if (probed % 50 === 0) {
      console.log(`[progress] probed=${probed} hits=${hits} last=${d}`);
    }
  }
  out.end();
  const elapsed = ((Date.now() - start) / 1000).toFixed(1);
  console.log(`\nDone. ${hits}/${TARGETS.length} domains had a public GS-compatible feed (${elapsed}s)`);
  console.log(`Output: ${outFile}`);
}

main().catch((e) => { console.error(e); process.exit(1); });
