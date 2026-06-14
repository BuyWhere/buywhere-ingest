// Unit tests for src/chunker.js (BUY-48425).
//
// chunkArray is the only thing standing between a Shopify deep-paged
// scrape (74 pages × 250 = 18,500 rows) and the /v1/ingest/products
// 1000-row cap. Off-by-one bugs here would either re-trigger the
// 72-minute INSERTs we're trying to kill, or return 400s for chunks
// the API could have accepted. The tests below pin both behaviours.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { chunkArray, chunkCount } from '../src/chunker.js';

test('chunkArray: empty array returns []', () => {
  assert.deepEqual(chunkArray([], 1000), []);
});

test('chunkArray: array shorter than size returns one chunk', () => {
  const arr = [1, 2, 3];
  assert.deepEqual(chunkArray(arr, 1000), [[1, 2, 3]]);
});

test('chunkArray: exact-multiple splits cleanly (1000 / 1000)', () => {
  const arr = Array.from({ length: 1000 }, (_, i) => i);
  const chunks = chunkArray(arr, 1000);
  assert.equal(chunks.length, 1);
  assert.equal(chunks[0].length, 1000);
  assert.equal(chunks[0][0], 0);
  assert.equal(chunks[0][999], 999);
});

test('chunkArray: 1001 rows over 1000-size limit → 2 chunks, last is 1', () => {
  const arr = Array.from({ length: 1001 }, (_, i) => i);
  const chunks = chunkArray(arr, 1000);
  assert.equal(chunks.length, 2);
  assert.equal(chunks[0].length, 1000);
  assert.equal(chunks[1].length, 1);
  assert.equal(chunks[1][0], 1000);
});

test('chunkArray: 18,500 rows (Shopify deep 7-80 × 250) → 19 chunks', () => {
  // (80-7+1) × 250 = 18,500; over 1000-cap that is ceil(18500/1000) = 19.
  // The last chunk is 500 rows, not 1000 — important: a chunk of exactly
  // 1000 + a chunk of 500 means one fewer request than 18 chunks of
  // 1000+500, which used to be the failure mode.
  const arr = Array.from({ length: 18500 }, (_, i) => i);
  const chunks = chunkArray(arr, 1000);
  assert.equal(chunks.length, 19);
  assert.equal(chunks[0].length, 1000);
  assert.equal(chunks[18].length, 500);
  assert.equal(chunks[18][0], 18000);
  assert.equal(chunks[18][499], 18499);
});

test('chunkArray: 10,000 rows (lane max 40 × 250) → 10 chunks', () => {
  const arr = Array.from({ length: 10000 }, (_, i) => i);
  const chunks = chunkArray(arr, 1000);
  assert.equal(chunks.length, 10);
  for (const c of chunks) assert.equal(c.length, 1000);
});

test('chunkArray: 8,000 rows (WC deep 80 × 100) → 8 chunks', () => {
  const arr = Array.from({ length: 8000 }, (_, i) => i);
  const chunks = chunkArray(arr, 1000);
  assert.equal(chunks.length, 8);
  for (const c of chunks) assert.equal(c.length, 1000);
});

test('chunkArray: odd batch size (size=7) handles non-divisible input', () => {
  const arr = Array.from({ length: 17 }, (_, i) => i);
  const chunks = chunkArray(arr, 7);
  assert.equal(chunks.length, 3); // ceil(17/7) = 3
  assert.deepEqual(chunks[0], [0, 1, 2, 3, 4, 5, 6]);
  assert.deepEqual(chunks[1], [7, 8, 9, 10, 11, 12, 13]);
  assert.deepEqual(chunks[2], [14, 15, 16]);
});

test('chunkArray: size=1 puts each element in its own chunk', () => {
  const arr = ['a', 'b', 'c'];
  const chunks = chunkArray(arr, 1);
  assert.deepEqual(chunks, [['a'], ['b'], ['c']]);
});

test('chunkArray: non-array input returns []', () => {
  assert.deepEqual(chunkArray(null, 1000), []);
  assert.deepEqual(chunkArray(undefined, 1000), []);
  assert.deepEqual(chunkArray('not-an-array', 1000), []);
  assert.deepEqual(chunkArray(42, 1000), []);
});

test('chunkArray: zero or negative size returns [] (defensive)', () => {
  assert.deepEqual(chunkArray([1, 2, 3], 0), []);
  assert.deepEqual(chunkArray([1, 2, 3], -1), []);
});

test('chunkArray: size larger than array returns one chunk of the array', () => {
  const arr = [1, 2, 3];
  const chunks = chunkArray(arr, 1000);
  assert.equal(chunks.length, 1);
  assert.deepEqual(chunks[0], [1, 2, 3]);
});

test('chunkCount: matches chunkArray length for representative inputs', () => {
  assert.equal(chunkCount(0, 1000), 0);
  assert.equal(chunkCount(1, 1000), 1);
  assert.equal(chunkCount(1000, 1000), 1);
  assert.equal(chunkCount(1001, 1000), 2);
  assert.equal(chunkCount(18500, 1000), 19);
  assert.equal(chunkCount(8000, 1000), 8);
  assert.equal(chunkCount(10000, 1000), 10);
});

test('chunkCount: invalid inputs return 0', () => {
  assert.equal(chunkCount(-1, 1000), 0);
  assert.equal(chunkCount(100, 0), 0);
  assert.equal(chunkCount(100, -5), 0);
  assert.equal(chunkCount('100', 1000), 0);
  assert.equal(chunkCount(null, 1000), 0);
});

test('chunkArray + chunkCount invariant: count equals chunks.length', () => {
  // Pin the contract — every input the worker might pass should
  // produce a chunks array of the length chunkCount predicted.
  for (const len of [0, 1, 250, 999, 1000, 1001, 2500, 8000, 10000, 18500, 100000]) {
    const arr = Array.from({ length: len }, (_, i) => i);
    const chunks = chunkArray(arr, 1000);
    assert.equal(chunks.length, chunkCount(len, 1000),
      `len=${len}: chunks.length=${chunks.length} !== chunkCount=${chunkCount(len, 1000)}`);
  }
});
