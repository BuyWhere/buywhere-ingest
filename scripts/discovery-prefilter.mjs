#!/usr/bin/env node
// scripts/discovery-prefilter.mjs
//
// BUY-32878: Pre-filter a domain list against e-commerce platform signatures.
// Input:  text file (one domain per line) OR stdin.
// Output: NDJSON records with detected platform, country hint, and product URL.

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
  body_timeout: 12000,
  headers_timeout: 8000,
  pipelining: 4,
  connections: 200,
}).compose(interceptors.redirect({ maxRedirections: 3 }));

const PLATFORM_PROBES = [
  {
    platform: "shopify",
    url: (d) => `https://${d}/products.json?limit=1`,
    accept: (body) => {
      if (!body) return false;
      try {
        const j = JSON.parse(body);
        return Array.isArray(j.products);
      } catch {
        return false;
      }
    },
  },
  {
    platform: "woocommerce",
    url: (d) => `https://${d}/wp-json/wc/v3/products?per_page=1`,
    accept: (body) => {
      if (!body) return false;
      try {
        const j = JSON.parse(body);
        return Array.isArray(j) || (typeof j === "object" && Array.isArray(j.data));
      } catch {
        return body.includes('"id"') && body.includes('"name"');
      }
    },
  },
  {
    platform: "magento",
    url: (d) => `https://${d}/rest/V1/products?searchCriteria[pageSize]=1`,
    accept: (body) => {
      if (!body) return false;
      try {
        const j = JSON.parse(body);
        return j && (Array.isArray(j.items) || typeof j === "object");
      } catch {
        return false;
      }
    },
  },
  {
    platform: "bigcommerce",
    url: (d) => `https://${d}/api/catalog/products?limit=1`,
    accept: (body) => {
      if (!body) return false;
      try {
        const j = JSON.parse(body);
        return j && (Array.isArray(j.data) || Array.isArray(j));
      } catch {
        return false;
      }
    },
  },
];

const TLD_COUNTRY = {
  sg: "SG", my: "MY", th: "TH", id: "ID", ph: "PH", vn: "VN",
  uk: "GB", de: "DE", fr: "FR", it: "IT", es: "ES", nl: "NL",
  jp: "JP", kr: "KR", cn: "CN", hk: "HK", tw: "TW", au: "AU",
  nz: "NZ", ca: "CA", mx: "MX", br: "BR", in: "IN",
};

const CURRENCY_TOKENS = {
  USD: ["usd", "$"],
  SGD: ["sgd", "s$"],
  MYR: ["myr", "rm"],
  THB: ["thb", "฿"],
  IDR: ["idr", "rp"],
  PHP: ["php", "₱"],
  VND: ["vnd", "₫"],
  GBP: ["gbp", "£"],
  EUR: ["eur", "€"],
  JPY: ["jpy", "¥"],
  AUD: ["aud", "a$"],
};

// Domains that are CDN/SaaS/tech infrastructure — NOT e-commerce stores.
// These pass HTML signature checks but have no products to deep-page.
const BLOCKED_DOMAINS = new Set([
  // Marketplaces / large retailers (skip — already scraped or blocked)
  "amazon.com", "amazon.co.uk", "amazon.de", "amazon.ca", "amazon.sg",
  "amazon.com.au", "amazon.co.jp", "amazon.in", "amazon.com.mx", "amazon.com.br",
  "amazon_jp", "amazon_us", "amazon_sg",
  "walmart.com", "target.com", "ebay.com", "bestbuy.com", "etsy.com",
  "homedepot.com", "wayfair.com", "overstock.com", "lowes.com",
  "costco.com", "ikea.com", "macys.com", "nordstrom.com",
  "alibaba.com", "aliexpress.com", "tmall.com", "jd.com", "taobao.com",
  "shopee", "lazada", "tokopedia", "qoo10", "rakuten", "coupang",
  // Tech giants
  "google.com", "facebook.com", "youtube.com", "twitter.com", "instagram.com",
  "github.com", "wikipedia.org", "reddit.com", "linkedinin.com",
  "apple.com", "microsoft.com", "netflix.com", "amazon.com",
  // CDN / edge / cloud infrastructure
  "cloudflare.com", "akamai.com", "fastly.com", "cloudfront.net",
  "cdn.cloudflare.com", ".edgesuite.net", "akamaiedge.net",
  "b-cdn.net", "cdn77.org", "cdnjs.cloudflare.com", "unpkg.com",
  "jsdelivr.net", "jsdelivr.com", "jquery.com", "jquerycdn.com",
  // SaaS / developer platforms (pass HTML signature but not stores)
  "wordpress.com", "wp.com", "wix.com", "squarespace.com", "shopify.com",
  "wixsite.com", "weebly.com", "bigcartel.com", "bigcommerce.com",
  "atlassian.net", "atlassian.com", "jira.com", "confluence.com",
  "github.com", "gitlab.com", "bitbucket.org", "github.io", "gitlab.io",
  "heroku.com", "vercel.com", "netlify.com", "cloudflare.com",
  "digitalocean.com", "linode.com", "vultr.com", "aws.amazon.com",
  "cloud.google.com", "azure.microsoft.com", "oracle.com",
  // Email / marketing automation
  "mailchimp.com", "sendgrid.net", "constantcontact.com", "hubspot.com",
  "marketo.com", "pardot.com", "eloqua.com", "mailgun.com",
  "postmarkapp.com", "sparkpost.com", "amazonses.com",
  // Analytics / tracking
  "google-analytics.com", "googletagmanager.com", "segment.io",
  "segment.com", "mixpanel.com", "amplitude.com", "heap.io",
  "hotjar.com", "crazyegg.com", "optimizely.com", "quantserve.com",
  // Customer service / live chat
  "intercom.io", "intercom.com", "zendesk.com", "freshdesk.com",
  "desk.com", "salesforce.com", "helpdesk.com",
  // URL shorteners / link management
  "bit.ly", "tinyurl.com", "goo.gl", "ow.ly", "t.co", "lnkd.in",
  "rebrandly.com", "short.io", "bitly.com",
  // Security / authentication
  "recaptcha.net", "hcaptcha.com", "cloudflare.com", "akamai.com",
  "forter.com", "riskified.com", "signifyd.com", "siftsf.com",
  // Payments / fintech
  "stripe.com", "paypal.com", "braintreepayments.com", "adyen.com",
  "squareup.com", "clover.com", "shopify.com", "woocommerce.com",
  // Push / notification
  "pusher.com", "onesignal.com", "airship.com", "urbanairship.com",
  "onesignal.org", "wonderpush.com",
  // Search / SEO
  "duckduckgo.com", "startpage.com", "yahoo.com", "bing.com", "baidu.com",
  "yandex.com", "naver.com", "seznam.cz",
  // Social / sharing
  "dropbox.com", "drive.google.com", "box.com", "onedrive.live.com",
  "slideshare.net", "scribd.com", "issuu.com", "calameo.com",
  // Translation / internationalization
  "deepl.com", "deepL.com", "translate.google.com", "babbel.com",
  // Storage / file hosting
  "drive.google.com", "mediafire.com", "dropbox.com", "wetransfer.com",
  "icoud.com", "icloud.com",
  // Misc tech (pass HTML sig, not stores)
  "cloudns.net", "dnsimple.com", "namecheap.com", "godaddy.com",
  "reg.ru", "uniregistry.com", "enom.com", "networkolutions.com",
  "workers.dev", "pages.dev", "vercel.app", "webflow.io",
  "shopify.com", "myshopify.com", "commercejs.com", "snipcart.com",
  "stripe.com", "bambora.com", "checkout.com", "klarna.com",
  "afterpay.com", "sezzle.com", "affirm.com", "paypal.com",
  // Productivity / office
  "slack.com", "teams.microsoft.com", "zoom.us", "webex.com",
  "asana.com", "trello.com", "monday.com", "notion.so",
  "evernote.com", "dropbox.com", "box.com", "zdassets.com",
  // Error / monitoring
  "sentry.io", "bugsnag.com", "rollbar.com", "airbrake.io",
  "newrelic.com", "datadog.com", "grafana.com", "splunk.com",
  // Login / identity
  "auth0.com", "okta.com", "onelogin.com", "pingidentity.com",
  "google.com", "facebook.com", "apple.com", "twitter.com",
  // VPN / proxy / networking
  "cloudflare.com", "nordvpn.com", "expressvpn.com", "ultrasurf.com",
  "hideMyAss.com", "protonvpn.com", "tunnelbear.com",
  // News / media / blogs
  "medium.com", "substack.com", "ghost.org", "substackcdn.com",
  "wixpress.com", "wordpress.com", "blogspot.com", "tumblr.com",
  // Video / streaming
  "vimeo.com", "dailymotion.com", "twitch.tv", "youtube.com",
  "googlevideo.com", "ytimg.com", "youtube-nocookie.com",
  // Misc infrastructure that slips through HTML detection
  "hcaptcha.com", "captcha.com", "recaptcha.net", "funcaptcha.com",
  "cloudflareinsights.com", "bugfender.com", "appdynamics.com",
  "newrelic.com", "applications.microsoft.com", "updates.microsoft.com",
  "office.com", "live.com", "msn.com", "bing.com", "msftconnecttest.com",
  "spotify.com", "soundcloud.com", "bandcamp.com", "tidal.com",
  "deezer.com", "pandora.com", "apple.com", "music.apple.com",
  "steampowered.com", "steamcommunity.com", "steamstatic.com",
  "discord.com", "slack.com", "telegram.org", "whatsapp.com",
  "zoom.us", "webex.com", "gotomeeting.com", "join.me",
  "teamviewer.com", "anydesk.com", "logmein.com",
]);

// Block parent domains (pass subdomain check but parent is not a store)
const BLOCKED_PARENTS = [
  "google.com", "microsoft.com", "amazon.com", "facebook.com",
  "apple.com", "cloudflare.com", "akamai.com", "fastly.com",
  "wordpress.com", "wix.com", "wixsite.com", "shopify.com",
  "atlassian.com", "github.com", "twitter.com", "t.co",
  "youtube.com", "instagram.com", "reddit.com", "wikipedia.org",
  "linkedin.com", "dropbox.com", "box.com", "slack.com",
  "zoom.us", "microsoftonline.com", "live.com", "office.com",
  "bing.com", "msn.com", "yahoo.com", "yahoo.co.jp",
  "baidu.com", "yandex.com", "mailchimp.com", "hubspot.com",
  "sendgrid.net", "stripe.com", "paypal.com", "braintreepayments.com",
  "intercom.io", "zendesk.com", "shopify.com", "woocommerce.com",
  "wp.com", "wordpress.com", "wixpress.com", "ghost.org",
  "sentry.io", "newrelic.com", "segment.io", "segment.com",
  "mixpanel.com", "amplitude.com", "heap.io", "hotjar.com",
  "digitalocean.com", "linode.com", "vultr.com", "heroku.com",
  "vercel.com", "netlify.com", "cloud.google.com", "azure.microsoft.com",
];

function parseArgs(argv) {
  const out = { input: null, output: null, concurrency: 100, timeoutMs: 8000, maxDomains: 0 };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--input") out.input = argv[++i];
    else if (a === "--output") out.output = argv[++i];
    else if (a === "--concurrency") out.concurrency = parseInt(argv[++i], 10);
    else if (a === "--timeout") out.timeoutMs = parseInt(argv[++i], 10);
    else if (a === "--max-domains") out.maxDomains = parseInt(argv[++i], 10);
  }
  return out;
}

async function readDomains(inputPath, maxDomains) {
  let raw;
  if (inputPath && inputPath !== "-") {
    raw = await fs.promises.readFile(inputPath, "utf8");
  } else {
    raw = await new Promise((resolve) => {
      let buf = "";
      process.stdin.setEncoding("utf8");
      process.stdin.on("data", (c) => (buf += c));
      process.stdin.on("end", () => resolve(buf));
    });
  }
  const seen = new Set();
  const out = [];
  for (const line of raw.split(/\r?\n/)) {
    const cleaned = line
      .trim()
      .toLowerCase()
      .replace(/^https?:\/\//, "")
      .replace(/\/.*$/, "")
      .replace(/:\d+$/, "");
    if (!cleaned || !/^[a-z0-9.-]+\.[a-z]{2,}$/.test(cleaned)) continue;
    if (BLOCKED_DOMAINS.has(cleaned)) continue;
    // Block subdomains of known non-store parents (e.g. cloudflare.com, wordpress.com)
    const parts = cleaned.split(".");
    if (parts.length >= 2) {
      const parent = parts.slice(-2).join(".");
      if (BLOCKED_PARENTS.includes(parent)) continue;
    }
    if (seen.has(cleaned)) continue;
    seen.add(cleaned);
    out.push(cleaned);
    if (maxDomains > 0 && out.length >= maxDomains) break;
  }
  return out;
}

function countryFromDomain(domain) {
  const parts = domain.split(".");
  const tld = parts[parts.length - 1];
  return TLD_COUNTRY[tld] || "US";
}

function detectCurrency(html) {
  if (!html) return null;
  const lower = html.toLowerCase();
  for (const [code, tokens] of Object.entries(CURRENCY_TOKENS)) {
    for (const tok of tokens) {
      if (lower.includes(`"${tok}`) || lower.includes(` ${tok} `) || lower.includes(`>${tok}<`)) {
        return code;
      }
    }
  }
  return null;
}

function detectSchemaProduct(html) {
  if (!html) return false;
  return /"@type"\s*:\s*"Product"/.test(html) || /application\/ld\+json[^<]+Product/.test(html);
}

async function probeUrl(url, timeoutMs) {
  const start = Date.now();
  try {
    const res = await request(url, {
      method: "GET",
      dispatcher: DISPATCHER,
      headers: {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        Accept: "application/json,text/html;q=0.9,*/*;q=0.5",
        "Accept-Language": "en-US,en;q=0.7",
      },
      bodyTimeout: timeoutMs,
      headersTimeout: timeoutMs,
    });
    if (res.statusCode >= 200 && res.statusCode < 300) {
      const text = await res.body.text();
      return { ok: true, status: res.statusCode, body: text, latency_ms: Date.now() - start };
    }
    await res.body.dump().catch(() => {});
    return { ok: false, status: res.statusCode, body: null, latency_ms: Date.now() - start };
  } catch (e) {
    return { ok: false, status: 0, body: null, error: e.message, latency_ms: Date.now() - start };
  }
}

async function detectDomain(domain, timeoutMs) {
  for (const check of PLATFORM_PROBES) {
    const url = check.url(domain);
    const r = await probeUrl(url, timeoutMs);
    if (r.ok && check.accept(r.body)) {
      return {
        domain,
        platform: check.platform,
        product_endpoint: url,
        probe_status: r.status,
        detection_method: "platform_endpoint",
        latency_ms: r.latency_ms,
      };
    }
    if (r.status === 429 || r.status >= 500) {
      await new Promise((res) => setTimeout(res, 200));
    }
  }
  // Fallback: homepage check
  const home = await probeUrl(`https://${domain}/`, timeoutMs);
  if (home.ok && home.body) {
    const html = home.body;
    if (/shopify/i.test(html)) {
      return { domain, platform: "shopify-html", product_endpoint: null, probe_status: home.status, detection_method: "html_signature", latency_ms: home.latency_ms };
    }
    if (/woocommerce/i.test(html) || /"wc":/i.test(html)) {
      return { domain, platform: "woocommerce-html", product_endpoint: null, probe_status: home.status, detection_method: "html_signature", latency_ms: home.latency_ms };
    }
    if (/magento/i.test(html)) {
      return { domain, platform: "magento-html", product_endpoint: null, probe_status: home.status, detection_method: "html_signature", latency_ms: home.latency_ms };
    }
    if (/bigcommerce/i.test(html)) {
      return { domain, platform: "bigcommerce-html", product_endpoint: null, probe_status: home.status, detection_method: "html_signature", latency_ms: home.latency_ms };
    }
    if (detectSchemaProduct(html)) {
      return { domain, platform: "schema-product", product_endpoint: null, probe_status: home.status, detection_method: "schema_org", latency_ms: home.latency_ms };
    }
  }
  return { domain, platform: "unknown", product_endpoint: null, probe_status: home.status ?? 0, detection_method: "fallback_no_match", latency_ms: home.latency_ms };
}

async function main() {
  const args = parseArgs(process.argv);
  if (!args.output) {
    console.error("Missing --output");
    process.exit(2);
  }
  const domains = await readDomains(args.input, args.maxDomains);
  console.error(`[prefilter] input=${args.input ?? "stdin"} domains=${domains.length} concurrency=${args.concurrency}`);

  const queue = [...domains];
  const results = [];
  const stats = {
    checked: 0,
    passed: 0,
    failed: 0,
    by_platform: {},
    started_at: new Date().toISOString(),
  };

  async function worker(id) {
    while (queue.length) {
      const d = queue.shift();
      if (!d) return;
      let result;
      try {
        const detected = await detectDomain(d, args.timeoutMs);
        const htmlCurrency = detected.platform.includes("html") || detected.platform === "schema-product"
          ? null
          : null;
        result = {
          ...detected,
          country_code: countryFromDomain(d),
          currency: htmlCurrency,
        };
      } catch (e) {
        result = { domain: d, platform: "error", error: e.message };
      }
      stats.checked++;
      if (result.platform && result.platform !== "unknown" && result.platform !== "error") {
        stats.passed++;
        stats.by_platform[result.platform] = (stats.by_platform[result.platform] || 0) + 1;
        results.push(result);
      } else {
        stats.failed++;
      }
      if (stats.checked % 50 === 0 || stats.checked === domains.length) {
        console.error(`[prefilter] worker=${id} checked=${stats.checked}/${domains.length} passed=${stats.passed} failed=${stats.failed} by_platform=${JSON.stringify(stats.by_platform)}`);
      }
    }
  }

  const workers = [];
  for (let i = 0; i < args.concurrency; i++) workers.push(worker(i));
  await Promise.all(workers);

  await fs.promises.mkdir(path.dirname(args.output), { recursive: true });
  const fh = await fs.promises.open(args.output, "w");
  for (const r of results) {
    await fh.write(JSON.stringify(r) + "\n");
  }
  await fh.close();
  stats.finished_at = new Date().toISOString();
  stats.output = args.output;
  stats.output_rows = results.length;
  console.error(`[prefilter] done: ${JSON.stringify(stats)}`);
}

main()
  .then(() => process.exit(0))
  .catch((e) => {
    console.error("[prefilter] fatal:", e);
    process.exit(1);
  });
