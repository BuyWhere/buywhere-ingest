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
      price: isNaN(price) ? 0 : price,
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