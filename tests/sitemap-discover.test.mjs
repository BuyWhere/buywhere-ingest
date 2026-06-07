// BUY-34837: Unit tests for src/sitemapDiscover.js
//
// These tests cover the parts that don't need a live sitemap fetch:
//   - parseSitemapXml() — sitemapindex vs urlset, malformed XML
//   - countryFromHost() — TLD/host → 2-letter ISO code
//   - validateSeedEntry() — required fields and shapes
//
// The fetch+walk path is exercised via the live /test-sitemap-walk
// endpoint on the buywhere-ingest service (pre-deploy smoke test) and
// not in unit tests, since it requires either a live sitemap server or
// a heavy mock that doesn't add much value over the endpoint.

import { test } from 'node:test';
import assert from 'node:assert/strict';

import {
  parseSitemapXml,
  countryFromHost,
  validateSeedEntry,
  SUPPORTED_KINDS,
  MIN_PRODUCTS_THRESHOLD,
} from '../src/sitemapDiscover.js';

test('SUPPORTED_KINDS exposes brand and retailer', () => {
  assert.deepEqual(SUPPORTED_KINDS, ['brand', 'retailer']);
});

test('MIN_PRODUCTS_THRESHOLD is 5 (the floor below which a sitemap is treated as empty)', () => {
  assert.equal(MIN_PRODUCTS_THRESHOLD, 5);
});

test('parseSitemapXml extracts locs from a urlset', () => {
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/p/1</loc></url>
  <url><loc>https://example.com/p/2</loc></url>
  <url><loc>https://example.com/p/3</loc></url>
</urlset>`;
  const r = parseSitemapXml(xml);
  assert.equal(r.ok, true);
  assert.equal(r.isIndex, false);
  assert.equal(r.locs.length, 3);
  assert.deepEqual(r.locs, [
    'https://example.com/p/1',
    'https://example.com/p/2',
    'https://example.com/p/3',
  ]);
});

test('parseSitemapXml flags sitemapindex documents as isIndex=true', () => {
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://example.com/sitemap-1.xml</loc></sitemap>
  <sitemap><loc>https://example.com/sitemap-2.xml</loc></sitemap>
</sitemapindex>`;
  const r = parseSitemapXml(xml);
  assert.equal(r.ok, true);
  assert.equal(r.isIndex, true);
  assert.equal(r.locs.length, 2);
  assert.deepEqual(r.locs, [
    'https://example.com/sitemap-1.xml',
    'https://example.com/sitemap-2.xml',
  ]);
});

test('parseSitemapXml returns empty (no throw) for malformed XML', () => {
  // xmldom is lenient with mismatched tags — it logs warnings but
  // doesn't always emit a <parsererror>. The contract is: the
  // function does not throw, and the result is either ok=false with
  // an error code, or ok=true with no extracted locs. Both are
  // acceptable — the walker's per-URL nulls will surface as 0
  // product URLs in the run summary either way.
  const xml = `<urlset><loc>https://example.com/p/1</wrong-tag></urlset>`;
  const r = parseSitemapXml(xml);
  assert.ok(r);
  assert.equal(typeof r.ok, 'boolean');
  assert.equal(typeof r.locs, 'object');
  assert.equal(Array.isArray(r.locs), true);
  // Either ok=false (xmldom emitted parsererror) or ok=true with 0 locs.
  if (r.ok) {
    assert.equal(r.locs.length, 0);
  } else {
    assert.ok(r.error);
  }
});

test('parseSitemapXml returns empty for null/empty input', () => {
  assert.equal(parseSitemapXml('').ok, false);
  assert.equal(parseSitemapXml(null).ok, false);
  assert.equal(parseSitemapXml(undefined).ok, false);
});

test('parseSitemapXml treats a document with no sitemapindex and no urlset as emptyShape', () => {
  const xml = `<?xml version="1.0" encoding="UTF-8"?><root></root>`;
  const r = parseSitemapXml(xml);
  assert.equal(r.ok, true);
  assert.equal(r.emptyShape, true);
  assert.equal(r.locs.length, 0);
});

test('countryFromHost maps common TLDs to ISO codes', () => {
  assert.equal(countryFromHost('nike.com'), 'US');
  assert.equal(countryFromHost('www.nike.com'), 'US');
  assert.equal(countryFromHost('bose.com'), 'US');
  assert.equal(countryFromHost('asos.co.uk'), 'GB');
  assert.equal(countryFromHost('uniqlo.jp'), 'JP');
  assert.equal(countryFromHost('uniqlo.co.jp'), 'JP');
  assert.equal(countryFromHost('kogan.com.au'), 'AU');
  assert.equal(countryFromHost('flipkart.in'), 'IN');
  assert.equal(countryFromHost('bestbuy.ca'), 'CA');
  assert.equal(countryFromHost('otto.de'), 'DE');
  assert.equal(countryFromHost('fnac.fr'), 'FR');
  assert.equal(countryFromHost('bol.nl'), 'NL');
  assert.equal(countryFromHost('lazada.sg'), 'SG');
});

test('countryFromHost defaults to US for unknown TLDs', () => {
  assert.equal(countryFromHost('example.unknown'), 'US');
  assert.equal(countryFromHost('foobar'), 'US');
  assert.equal(countryFromHost(''), 'US');
  assert.equal(countryFromHost(null), 'US');
});

test('validateSeedEntry accepts a fully-populated brand entry', () => {
  const entry = {
    domain: 'nike.com',
    source: 'brand_nike',
    country: 'US',
    uaMode: 'bot',
    sitemaps: ['https://www.nike.com/sitemap_products.xml'],
    productPattern: '^https://www\\.nike\\.com/t/',
  };
  const v = validateSeedEntry(entry);
  assert.equal(v.ok, true);
  assert.deepEqual(v.errors, []);
});

test('validateSeedEntry rejects entries with missing fields', () => {
  const v1 = validateSeedEntry({});
  assert.equal(v1.ok, false);
  assert.ok(v1.errors.includes('invalid_domain'));
  assert.ok(v1.errors.includes('missing_sitemaps'));
  assert.ok(v1.errors.includes('missing_productPattern'));
  assert.ok(v1.errors.includes('missing_source'));

  const v2 = validateSeedEntry({
    domain: 'nike.com',
    source: 'brand_nike',
    productPattern: 'p/',
    sitemaps: ['not-a-url'],
  });
  assert.equal(v2.ok, false);
  assert.ok(v2.errors.some((e) => e.startsWith('bad_sitemap')));

  const v3 = validateSeedEntry({
    domain: 'no-dot',
    source: 's',
    productPattern: 'p/',
    sitemaps: ['https://x.com/sitemap.xml'],
  });
  assert.equal(v3.ok, false);
  assert.ok(v3.errors.includes('invalid_domain'));
});

test('validateSeedEntry rejects bad uaMode', () => {
  const v = validateSeedEntry({
    domain: 'nike.com',
    source: 's',
    productPattern: 'p/',
    sitemaps: ['https://x.com/sitemap.xml'],
    uaMode: 'mobile',  // not in {bot,desktop}
  });
  assert.equal(v.ok, false);
  assert.ok(v.errors.includes('bad_uaMode'));
});

test('validateSeedEntry accepts desktop uaMode', () => {
  const v = validateSeedEntry({
    domain: 'macys.com',
    source: 's',
    productPattern: 'p/',
    sitemaps: ['https://x.com/sitemap.xml'],
    uaMode: 'desktop',
  });
  assert.equal(v.ok, true);
});

test('validateSeedEntry accepts entry without uaMode (defaults to bot)', () => {
  const v = validateSeedEntry({
    domain: 'nike.com',
    source: 's',
    productPattern: 'p/',
    sitemaps: ['https://x.com/sitemap.xml'],
  });
  assert.equal(v.ok, true);
});
