// Unit tests for src/trancoDiscovery.js — the platform fingerprint
// probes + the Tranco list parser. Uses node:test (built into Node 20+,
// matches the Dockerfile's node:20-alpine base).
//
// All HTTP probes (probeWooCommerce / probeMagento / probeBigCommerce /
// probeCustom) accept an `opts.fetchImpl` injection point so the suite
// is hermetic and doesn't hit the public internet. Run with:
//
//   npm test
//
// which is wired to `node --test tests/`.

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  fetchTrancoList,
  probeWooCommerce,
  probeMagento,
  probeBigCommerce,
  probeCustom,
  probeTrancoHost,
  SUPPORTED_KINDS,
} from '../src/trancoDiscovery.js';

// A helper to build a Response with a JSON body.
function jsonResponse(body, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json', ...extraHeaders },
  });
}
function textResponse(body, status = 200, extraHeaders = {}) {
  return new Response(body, { status, headers: extraHeaders });
}

// A mock fetch that routes by URL substring.
function mockFetchByUrl(routes) {
  return async (url, init = {}) => {
    for (const [pattern, responder] of routes) {
      if (typeof pattern === 'string' ? url.includes(pattern) : pattern.test(url)) {
        return await responder(url, init);
      }
    }
    return new Response('not found', { status: 404 });
  };
}

// ---------------------------------------------------------------------------
// fetchTrancoList
// ---------------------------------------------------------------------------

describe('fetchTrancoList', () => {
  it('parses a well-formed Tranco CSV into rank/domain rows', async () => {
    const csv = [
      'rank,domain',
      '1,google.com',
      '2,facebook.com',
      '3,amazon.com',
      '',
      '# trailing comment line',
      'malformed line without a comma',
      '5,wordpress.com',
    ].join('\n');
    const fetchImpl = mockFetchByUrl([
      ['/api/lists/latest', async () => jsonResponse({ list_id: 'L1', available_date: '2026-06-07' })],
      ['/lists/L1/full', async () => textResponse(csv, 200, { 'content-type': 'text/csv' })],
    ]);
    // No listId — the producer path always starts with the latest-list
    // metadata fetch, which yields availableDate.
    const out = await fetchTrancoList({ fetchImpl });
    assert.equal(out.listId, 'L1');
    assert.equal(out.availableDate, '2026-06-07');
    assert.equal(out.rows.length, 4);
    assert.deepEqual(out.rows[0], { rank: 1, domain: 'google.com' });
    assert.deepEqual(out.rows[3], { rank: 5, domain: 'wordpress.com' });
  });

  it('skips metadata fetch when listId is supplied', async () => {
    const csv = 'rank,domain\n1,a.com\n';
    const fetchImpl = mockFetchByUrl([
      ['/lists/L-PINNED/full', async () => textResponse(csv, 200, { 'content-type': 'text/csv' })],
    ]);
    const out = await fetchTrancoList({ fetchImpl, listId: 'L-PINNED' });
    assert.equal(out.listId, 'L-PINNED');
    assert.equal(out.availableDate, null);
    assert.equal(out.rows.length, 1);
  });

  it('honors the limit option', async () => {
    const csv = 'rank,domain\n1,a.com\n2,b.com\n3,c.com\n';
    const fetchImpl = mockFetchByUrl([
      ['/api/lists/latest', async () => jsonResponse({ list_id: 'L2' })],
      ['/lists/L2/full', async () => textResponse(csv, 200, { 'content-type': 'text/csv' })],
    ]);
    const out = await fetchTrancoList({ fetchImpl, limit: 2 });
    assert.equal(out.rows.length, 2);
    assert.deepEqual(out.rows.map((r) => r.rank), [1, 2]);
  });

  it('rejects on missing list_id metadata', async () => {
    const fetchImpl = mockFetchByUrl([
      ['/api/lists/latest', async () => jsonResponse({})],
    ]);
    await assert.rejects(() => fetchTrancoList({ fetchImpl }), /list_id/);
  });

  it('surfaces upstream 500 from the metadata endpoint', async () => {
    const fetchImpl = mockFetchByUrl([
      ['/api/lists/latest', async () => new Response('upstream down', { status: 500 })],
    ]);
    await assert.rejects(
      () => fetchTrancoList({ fetchImpl, fetchTimeoutMs: 1000 }),
      /Tranco list metadata fetch failed/
    );
  });

  it('surfaces upstream 500 from the csv endpoint', async () => {
    const fetchImpl = mockFetchByUrl([
      ['/api/lists/latest', async () => jsonResponse({ list_id: 'L9' })],
      ['/lists/L9/full', async () => new Response('csv service down', { status: 503 })],
    ]);
    await assert.rejects(
      () => fetchTrancoList({ fetchImpl, fetchTimeoutMs: 1000 }),
      /Tranco list csv fetch failed/
    );
  });
});

// ---------------------------------------------------------------------------
// probeWooCommerce
// ---------------------------------------------------------------------------

describe('probeWooCommerce', () => {
  it('returns ok=true on a real WC Store API response', async () => {
    const fetchImpl = mockFetchByUrl([
      ['/wp-json/wc/store/products', async () => jsonResponse([
        { id: 42, name: 'Cool Mug', prices: { price: '1500', currency_code: 'USD' } },
      ])],
    ]);
    const r = await probeWooCommerce('example.com', 5000, { fetchImpl });
    assert.equal(r.ok, true);
    assert.equal(r.kind, 'woocommerce');
    assert.equal(r.evidence.productCount, 1);
    assert.equal(r.evidence.firstProductId, 42);
    assert.equal(r.evidence.firstProductName, 'Cool Mug');
  });

  it('returns ok=false on empty array', async () => {
    const fetchImpl = mockFetchByUrl([
      ['/wp-json/wc/store/products', async () => jsonResponse([])],
    ]);
    const r = await probeWooCommerce('example.com', 5000, { fetchImpl });
    assert.equal(r.ok, false);
    assert.equal(r.reason, 'empty_or_not_array');
  });

  it('returns ok=false on non-JSON content type', async () => {
    const fetchImpl = mockFetchByUrl([
      ['/wp-json/wc/store/products', async () => textResponse('<html>oops</html>', 200, { 'content-type': 'text/html' })],
    ]);
    const r = await probeWooCommerce('example.com', 5000, { fetchImpl });
    assert.equal(r.ok, false);
    assert.equal(r.reason, 'no_response');
  });

  it('returns ok=false on 404', async () => {
    const fetchImpl = mockFetchByUrl([
      ['/wp-json/wc/store/products', async () => new Response('not found', { status: 404 })],
    ]);
    const r = await probeWooCommerce('example.com', 5000, { fetchImpl });
    assert.equal(r.ok, false);
    assert.equal(r.reason, 'no_response');
  });
});

// ---------------------------------------------------------------------------
// probeMagento
// ---------------------------------------------------------------------------

describe('probeMagento', () => {
  it('returns ok=true on a real Magento REST response', async () => {
    const fetchImpl = mockFetchByUrl([
      ['/rest/V1/products', async () => jsonResponse({
        items: [{ id: 1, sku: 'SKU-1', name: 'Hat' }],
        search_criteria: { page_size: 1 },
      }, 200, { 'x-magento-cache-id': 'abc' })],
    ]);
    const r = await probeMagento('example.com', 5000, { fetchImpl });
    assert.equal(r.ok, true);
    assert.equal(r.kind, 'magento');
    assert.equal(r.evidence.firstProductSku, 'SKU-1');
    assert.equal(r.evidence.magentoHeader, 'x-magento-cache-id');
  });

  it('returns ok=true on a Magento debug header alone (no body shape)', async () => {
    const fetchImpl = mockFetchByUrl([
      ['/rest/V1/products', async () => new Response('', { status: 200, headers: { 'x-magento-tags': 'foo' } })],
    ]);
    const r = await probeMagento('example.com', 5000, { fetchImpl });
    // No items + no items-array shape — not a positive hit, even with the
    // header. The header alone is not enough because JSON is also required.
    assert.equal(r.ok, false);
  });

  it('returns ok=false on a non-Magento JSON shape', async () => {
    const fetchImpl = mockFetchByUrl([
      ['/rest/V1/products', async () => jsonResponse({ message: 'unauthorized' }, 200)],
    ]);
    const r = await probeMagento('example.com', 5000, { fetchImpl });
    assert.equal(r.ok, false);
    assert.equal(r.reason, 'not_magento_shape');
  });
});

// ---------------------------------------------------------------------------
// probeBigCommerce
// ---------------------------------------------------------------------------

describe('probeBigCommerce', () => {
  it('returns ok=true on a real BigCommerce Storefront response', async () => {
    const fetchImpl = mockFetchByUrl([
      ['/api/storefront/products', async () => jsonResponse({
        data: [{ id: 7, name: 'BC Hat' }],
        meta: { pagination: { total: 1 } },
      })],
    ]);
    const r = await probeBigCommerce('example.com', 5000, { fetchImpl });
    assert.equal(r.ok, true);
    assert.equal(r.kind, 'bigcommerce');
    assert.equal(r.evidence.firstProductId, 7);
  });

  it('returns ok=false on a non-BC JSON shape', async () => {
    const fetchImpl = mockFetchByUrl([
      ['/api/storefront/products', async () => jsonResponse([{ id: 1 }])],
    ]);
    const r = await probeBigCommerce('example.com', 5000, { fetchImpl });
    assert.equal(r.ok, false);
    assert.equal(r.reason, 'not_bigcommerce_shape');
  });
});

// ---------------------------------------------------------------------------
// probeCustom
// ---------------------------------------------------------------------------

describe('probeCustom', () => {
  it('returns ok=true on homepage with /products/ links', async () => {
    const html = '<html><body><a href="/products/foo">Foo</a></body></html>';
    const fetchImpl = mockFetchByUrl([
      ['/', async () => textResponse(html, 200, { 'content-type': 'text/html; charset=utf-8' })],
    ]);
    const r = await probeCustom('example.com', 5000, { fetchImpl });
    assert.equal(r.ok, true);
    assert.equal(r.kind, 'custom');
    assert.equal(r.low_confidence, true);
    assert.equal(r.evidence.exampleUrl, '/products/foo');
  });

  it('returns ok=true on homepage with /collections/ links', async () => {
    const html = '<html><body><a href="/collections/all">All</a></body></html>';
    const fetchImpl = mockFetchByUrl([
      ['/', async () => textResponse(html, 200, { 'content-type': 'text/html' })],
    ]);
    const r = await probeCustom('example.com', 5000, { fetchImpl });
    assert.equal(r.ok, true);
    assert.equal(r.kind, 'custom');
  });

  it('returns ok=false on a homepage with no product URLs', async () => {
    const html = '<html><body><h1>About us</h1></body></html>';
    const fetchImpl = mockFetchByUrl([
      ['/', async () => textResponse(html, 200, { 'content-type': 'text/html' })],
    ]);
    const r = await probeCustom('example.com', 5000, { fetchImpl });
    assert.equal(r.ok, false);
    assert.equal(r.reason, 'no_product_url_pattern');
  });

  it('returns ok=false on non-HTML content type', async () => {
    const fetchImpl = mockFetchByUrl([
      ['/', async () => jsonResponse({ msg: 'hi' }, 200, { 'content-type': 'application/json' })],
    ]);
    const r = await probeCustom('example.com', 5000, { fetchImpl });
    assert.equal(r.ok, false);
    assert.equal(r.reason, 'not_html');
  });
});

// ---------------------------------------------------------------------------
// probeTrancoHost (entry point with kind dispatch)
// ---------------------------------------------------------------------------

describe('probeTrancoHost', () => {
  it('rejects invalid host', async () => {
    const r = await probeTrancoHost('', 'woocommerce');
    assert.equal(r.ok, false);
    assert.equal(r.reason, 'invalid_host');
  });

  it('rejects host without a dot', async () => {
    const r = await probeTrancoHost('localhost', 'woocommerce');
    assert.equal(r.ok, false);
    assert.equal(r.reason, 'invalid_host');
  });

  it('rejects unsupported kind', async () => {
    const r = await probeTrancoHost('example.com', 'joomla');
    assert.equal(r.ok, false);
    assert.match(r.reason, /unsupported_kind/);
  });

  it('routes to the correct probe and adds the source label', async () => {
    const fetchImpl = mockFetchByUrl([
      ['/wp-json/wc/store/products', async () => jsonResponse([{ id: 1, name: 'X' }])],
    ]);
    const r = await probeTrancoHost('example.com', 'woocommerce', 5000, { fetchImpl });
    assert.equal(r.ok, true);
    assert.equal(r.kind, 'woocommerce');
    assert.equal(r.source, 'tranco_woocommerce');
  });

  it('exposes SUPPORTED_KINDS as the canonical kind list', () => {
    assert.deepEqual(SUPPORTED_KINDS, ['woocommerce', 'magento', 'bigcommerce', 'custom']);
  });

  it('returns ok=false with a structured reason when the probe fails', async () => {
    const fetchImpl = mockFetchByUrl([
      ['/wp-json/wc/store/products', async () => new Response('', { status: 500 })],
    ]);
    const r = await probeTrancoHost('example.com', 'woocommerce', 5000, { fetchImpl });
    assert.equal(r.ok, false);
    assert.equal(r.reason, 'no_response');
    // source is NOT added on a negative result (only on ok)
    assert.equal(r.source, undefined);
  });
});
