// BUY-48425: array chunker for /v1/ingest/products batch commits.
//
// The API caps each request at 1000 products (see api/src/routes/ingest.ts:205
// — "Maximum 1000 products per request"). Workers that scrape a whole
// merchant in one job (e.g. DEEP_QUEUE with pages 7-80 × 250 = 18.5K rows,
// or lane runners with 40 pages × 250 = 10K rows) MUST split the payload
// into ≤1000-row chunks so each chunk becomes its own short transaction
// — the previous single-call shape held row locks for hours, blocked
// autovacuum's cleanup lock, and (when the 1000 cap was added) left
// runs stuck in a failed-but-not-marked state.
//
// Pure helper — no I/O, no env access. The caller passes the batch size
// explicitly so this module can be unit-tested without a database.

export function chunkArray(arr, size) {
  if (!Array.isArray(arr) || size <= 0) return [];
  const out = [];
  for (let i = 0; i < arr.length; i += size) out.push(arr.slice(i, i + size));
  return out;
}

// Number of full chunks (and the size of the trailing partial chunk, if
// any) for a given array length. Useful for tests and progress logging.
export function chunkCount(arrLength, size) {
  if (typeof arrLength !== 'number' || arrLength < 0 || size <= 0) return 0;
  return Math.ceil(arrLength / size);
}
