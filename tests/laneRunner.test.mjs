// Unit tests for src/laneRunner.js (BUY-34838).
//
// Covers the quality filter (mirrors scripts/lib/buy30620-discovery-common.mjs
// evaluateQuality) and the lane products → /v1/ingest/products transform.
// The fetcher itself hits the network, so we only test the pure helpers.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  evaluateLaneQuality,
  laneProductsToIngestRows,
  LANE_ROLES,
  LANE_ROLE_CONFIG,
} from '../src/laneRunner.js';

const goodProduct = (i) => ({
  id: `p${i}`,
  title: `Product ${i}`,
  handle: `product-${i}`,
  price: `${10 + i}.00`,
  variants: [{ price: `${10 + i}.00` }],
  vendor: 'Acme',
  product_type: 'Shoes',
  images: [{ src: `https://cdn.example.com/p${i}.jpg` }],
});

test('LANE_ROLES contains the 5 expected lane names', () => {
  assert.deepEqual([...LANE_ROLES].sort(), ['crate', 'hunt', 'hunt2', 'scout', 'stock']);
});

test('LANE_ROLE_CONFIG has a config for every role', () => {
  for (const role of LANE_ROLES) {
    const cfg = LANE_ROLE_CONFIG[role];
    assert.ok(cfg, `missing config for role ${role}`);
    assert.ok(typeof cfg.defaultConcurrency === 'number');
    assert.ok(['strict', 'light'].includes(cfg.qualityMode));
    assert.ok(cfg.maxPages > 0);
    assert.ok(cfg.fetchTimeoutMs > 0);
  }
});

test('evaluateLaneQuality: empty products fail', () => {
  const r = evaluateLaneQuality([], { mode: 'strict' });
  assert.equal(r.pass, false);
  assert.equal(r.reason, 'no-products');
});

test('evaluateLaneQuality: strict mode rejects no-numeric-price batch', () => {
  const products = Array.from({ length: 6 }, (_, i) => ({
    ...goodProduct(i),
    price: null,
    variants: [],
  }));
  const r = evaluateLaneQuality(products, { mode: 'strict' });
  assert.equal(r.pass, false);
  assert.equal(r.reason, 'no-numeric-price');
});

test('evaluateLaneQuality: light mode accepts no-numeric-price batch with varied metadata', () => {
  const products = Array.from({ length: 10 }, (_, i) => ({
    ...goodProduct(i),
    price: null,
    variants: [],
  }));
  const r = evaluateLaneQuality(products, { mode: 'light' });
  assert.equal(r.pass, true, JSON.stringify(r));
});

test('evaluateLaneQuality: rejects likely-fabricated batch (single price + blank images)', () => {
  const products = Array.from({ length: 10 }, (_, i) => ({
    id: `p${i}`,
    title: `Product ${i}`,
    handle: `product-${i}`,
    price: '9.99',
    variants: [{ price: '9.99' }],
    vendor: 'Acme',
    product_type: 'Shoes',
    images: [], // no images at all
  }));
  const r = evaluateLaneQuality(products, { mode: 'strict' });
  assert.equal(r.pass, false);
  assert.equal(r.reason, 'likely-fabricated-batch');
});

test('evaluateLaneQuality: accepts a normal healthy batch', () => {
  const products = Array.from({ length: 30 }, (_, i) => goodProduct(i));
  const r = evaluateLaneQuality(products, { mode: 'strict' });
  assert.equal(r.pass, true, JSON.stringify(r));
  assert.equal(r.metrics.productCount, 30);
  assert.ok(r.metrics.uniquePriceCount > 1);
});

test('evaluateLaneQuality: rejects > 50% placeholder ratio on >= 6 products', () => {
  const products = [];
  for (let i = 0; i < 4; i++) products.push(goodProduct(i));
  for (let i = 0; i < 6; i++) {
    products.push({
      id: `placeholder${i}`,
      title: 'placeholder product',
      handle: `placeholder-${i}`,
      price: '5.00',
      variants: [{ price: '5.00' }],
      vendor: 'Test',
      product_type: 'Test',
      images: [{ src: 'https://cdn.example.com/p.jpg' }],
    });
  }
  const r = evaluateLaneQuality(products, { mode: 'light' });
  assert.equal(r.pass, false);
  assert.equal(r.reason, 'placeholder-like-product-ratio');
});

test('laneProductsToIngestRows: maps products to ingest shape with stable sku key', () => {
  const products = [
    { id: 'abc', title: 'X', handle: 'x', price: 5, vendor: 'Acme', product_type: 'A', image: 'https://i/x.jpg', available: true, url: 'https://d/products/x', role: 'hunt' },
  ];
  const rows = laneProductsToIngestRows(products, 'shop.example');
  assert.equal(rows.length, 1);
  const r = rows[0];
  assert.equal(r.sku, 'shop.example-abc');
  assert.equal(r.merchant_id, 'shop.example');
  assert.equal(r.title, 'X');
  assert.equal(r.price, 5);
  assert.equal(r.image_url, 'https://i/x.jpg');
  assert.equal(r.is_active, true);
  assert.equal(r.is_available, true);
  assert.equal(r.metadata.shopify_domain, 'shop.example');
  assert.equal(r.metadata.lane_role, 'hunt');
  assert.equal(r.metadata.handle, 'x');
});

test('laneProductsToIngestRows: coerces null price to 0', () => {
  const rows = laneProductsToIngestRows(
    [{ id: '1', title: 'Y', handle: 'y', price: null, vendor: 'B', product_type: 'B', image: null, available: true, url: 'https://d', role: 'hunt' }],
    'shop.example'
  );
  assert.equal(rows[0].price, 0);
  assert.equal(rows[0].image_url, null);
});
