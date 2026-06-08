import https from 'https';
import http from 'http';
import { DOMParser } from 'xmldom';

const TIMEOUT = 15000;

function httpGet(url, timeout = TIMEOUT) {
  return new Promise((resolve, reject) => {
    const client = url.startsWith('https') ? https : http;
    const req = client.get(url, {
      timeout,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/xml, application/xhtml+xml, text/html, */*'
      }
    }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        resolve({ status: res.statusCode, headers: res.headers, body: data });
      });
    });
    req.on('error', reject);
    req.on('timeout', () => { req.destroy(); reject(new Error('Timeout')); });
  });
}

function parseXmlSitemap(xml) {
  const urls = [];
  try {
    const parser = new DOMParser();
    const doc = parser.parseFromString(xml, 'text/xml');
    const err = doc.getElementsByTagName('parsererror');
    if (err.length > 0) return { error: 'invalid_xml', urls };

    const sitemapindex = doc.getElementsByTagName('sitemapindex');
    if (sitemapindex.length > 0) {
      const sitemaps = doc.getElementsByTagName('sitemap');
      for (let i = 0; i < sitemaps.length; i++) {
        const loc = sitemaps[i].getElementsByTagName('loc')[0];
        if (loc) urls.push({ type: 'sitemap', url: loc.textContent });
      }
    }

    const urlset = doc.getElementsByTagName('urlset');
    if (urlset.length > 0) {
      const locs = doc.getElementsByTagName('loc');
      for (let i = 0; i < locs.length; i++) {
        urls.push({ type: 'url', url: locs[i].textContent });
      }
    }
  } catch (e) {
    return { error: e.message, urls };
  }
  return { error: null, urls };
}

function extractJsonLd(html) {
  const jsonLdItems = [];
  const regex = /<script[^>]*type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi;
  let match;
  while ((match = regex.exec(html)) !== null) {
    try {
      const parsed = JSON.parse(match[1]);
      jsonLdItems.push(Array.isArray(parsed) ? parsed : [parsed]);
    } catch (e) {
    }
  }
  return jsonLdItems.flat();
}

function extractMetaTags(html) {
  const metaTags = {};
  const titleMatch = html.match(/<title[^>]*>([^<]+)<\/title>/i);
  if (titleMatch) metaTags.title = titleMatch[1].trim();

  const descMatch = html.match(/<meta[^>]+name=["']description["'][^>]+content=["']([^"']+)["']/i);
  if (descMatch) metaTags.description = descMatch[1];

  return metaTags;
}

async function scrapePDP(url, domain) {
  try {
    const response = await httpGet(url);
    if (response.status !== 200) return null;

    const jsonLd = extractJsonLd(response.body);
    const meta = extractMetaTags(response.body);

    let productData = null;
    for (const item of jsonLd) {
      if (item['@type'] === 'Product' || (item['@graph'] && Array.isArray(item['@graph']))) {
        const graph = item['@graph'] || [item];
        for (const g of graph) {
          if (g['@type'] === 'Product') {
            productData = g;
            break;
          }
        }
        if (productData) break;
      }
    }

    if (!productData) return null;

    const offers = productData.offers && productData.offers[0] ? productData.offers[0] : {};
    const price = typeof offers.price === 'number' ? offers.price : parseFloat(offers.price);
    const currency = offers.priceCurrency || 'USD';
    
    const sku = productData.sku || url.split('/').filter(Boolean).pop();
    
    return {
      sku: `${domain}-${sku}`,
      merchant_id: domain,
      title: productData.name || meta.title || '',
      description: productData.description || meta.description || '',
      price: isNaN(price) ? null : price,
      currency: currency,
      url: url,
      image_url: productData.image || (Array.isArray(productData.image) ? productData.image[0] : null),
      brand: productData.brand?.name || productData.brand || null,
      is_active: true,
      is_available: offers.availability === 'https://schema.org/InStock' || offers.availability === 'InStock',
      metadata: {
        shopify_domain: domain,
        scraped_at: new Date().toISOString(),
      }
    };
  } catch (e) {
    console.error(`[scraper] Error scraping PDP ${url}:`, e.message);
    return null;
  }
}

function extractPriceFromVariants(p) {
  const variants = p.variants || [];
  const prices = variants
    .map((v) => (v && v.price != null ? parseFloat(v.price) : null))
    .filter((x) => x != null && !Number.isNaN(x));
  return prices.length ? Math.min(...prices) : null;
}

// BUY-34833: deep-page variant of scrapeShopifyStore. Same output shape so the
// existing ingestProductsToCatalog path in worker.js accepts it without a
// branch. Uses Shopify's /products.json?page=N&limit=250 paginated endpoint
// (sitemaps only cover the first ~250-5000 PDPs; deep paging must hit the
// products.json endpoint directly, per buy30590-deep-page-loop.mjs which is
// the source script being migrated).
//
// Stops on the first page that returns < limit products (end of catalog) or
// returns 0 products. Returns the same `{sku, merchant_id, title, ...}`
// shape as scrapeShopifyStore so worker.js can ingest with one call.
export async function scrapeShopifyStorePages(domain, startPage = 7, endPage = 80, limit = 250) {
  console.log(`[scraper] deep-page starting for ${domain} pages=${startPage}-${endPage} limit=${limit}`);
  const all = [];
  let lastPage = startPage - 1;

  for (let page = startPage; page <= endPage; page++) {
    const url = `https://${domain}/products.json?limit=${limit}&page=${page}`;
    const products = await fetchShopifyJsonPage(domain, url);
    if (!products || products.length === 0) {
      console.log(`[scraper] deep-page ${domain} page=${page} returned 0 → stop`);
      break;
    }
    lastPage = page;

    for (const p of products) {
      const handle = p.handle || '';
      const url = handle ? `https://${domain}/products/${handle}` : `https://${domain}`;
      const price = extractPriceFromVariants(p);
      const image = Array.isArray(p.images) && p.images.length > 0
        ? (p.images[0] && p.images[0].src) || null
        : null;
      const firstVariant = Array.isArray(p.variants) && p.variants.length > 0
        ? p.variants[0]
        : null;
      all.push({
        sku: `${domain}-${p.id}`,
        merchant_id: domain,
        title: p.title || '',
        description: p.body_html || '',
        price: price == null ? null : price,
        currency: 'USD',
        url,
        image_url: image,
        brand: p.vendor || null,
        is_active: true,
        is_available: firstVariant ? firstVariant.available !== false : true,
        metadata: {
          shopify_domain: domain,
          scraped_at: new Date().toISOString(),
          deep_page: page,
          handle,
          product_type: p.product_type || null,
        },
      });
    }

    // End-of-catalog signal: a non-full page means we hit the tail.
    if (products.length < limit) {
      console.log(`[scraper] deep-page ${domain} page=${page} returned ${products.length} < ${limit} → stop`);
      break;
    }
  }

  console.log(`[scraper] deep-page ${domain} done: pages=${startPage}-${lastPage} products=${all.length}`);
  return all;
}

async function fetchShopifyJsonPage(domain, url) {
  const TIMEOUT = 15000;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT);
  try {
    const res = await fetch(url, {
      signal: controller.signal,
      headers: {
        'User-Agent': 'Mozilla/5.0 (compatible; BuywhereDeepBot/1.0)',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) return null;
    const text = await res.text();
    if (!text.includes('"products"')) return null;
    const data = JSON.parse(text);
    return Array.isArray(data.products) ? data.products : null;
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

export async function scrapeShopifyStore(domain, maxProducts = 100) {
  console.log(`[scraper] Starting scrape for ${domain}`);
  
  try {
    const sitemapIndexUrl = `https://${domain}/sitemap.xml`;
    const sitemapResponse = await httpGet(sitemapIndexUrl);

    if (!sitemapResponse.body.includes('<?xml')) {
      console.error(`[scraper] Not an XML sitemap for ${domain}`);
      return [];
    }

    const parsed = parseXmlSitemap(sitemapResponse.body);
    console.log(`[scraper] Found ${parsed.urls.length} sitemap entries for ${domain}`);

    const productSitemap = parsed.urls.find(u => u.url.includes('sitemap_products'));
    if (!productSitemap) {
      console.error(`[scraper] No product sitemap found for ${domain}`);
      return [];
    }

    console.log(`[scraper] Fetching product sitemap: ${productSitemap.url}`);
    const productResponse = await httpGet(productSitemap.url);
    const productUrls = parseXmlSitemap(productResponse.body).urls.filter(u => 
      u.url.includes('/products/') && !u.url.includes('/collections/')
    );

    console.log(`[scraper] Found ${productUrls.length} product URLs for ${domain}`);

    const products = [];
    const limit = Math.min(maxProducts, productUrls.length);
    
    for (let i = 0; i < limit; i++) {
      const entry = productUrls[i];
      process.stdout.write(`\r[scraper] Processing ${i + 1}/${limit} products from ${domain}  `);
      
      const product = await scrapePDP(entry.url, domain);
      if (product) {
        products.push(product);
      }
      
      if (i < limit - 1) {
        await new Promise(resolve => setTimeout(resolve, 100));
      }
    }
    
    console.log(`\n[scraper] Completed scrape for ${domain}: ${products.length} products`);
    return products;
  } catch (e) {
    console.error(`[scraper] Error scraping store ${domain}:`, e.message);
    return [];
  }
}