/**
 * Checkpoint B: Pre-INSERT fabrication gate for R2 batch ingestion.
 *
 * Refuses to proceed if the batch contains fabricated data using three signals:
 *   - zero_price share > ZERO_PRICE_MAX_PCT (5%)
 *   - null_image share > NULL_IMAGE_MAX_PCT (50%)
 *   - placeholder_title share > PLACEHOLDER_TITLE_MAX_PCT (10%)
 *
 * A "placeholder title" matches the pattern "eBay item <id>" produced when the
 * eBay scraper walks item-ID lists instead of item pages (BUY-22153 incident class).
 */

export const ZERO_PRICE_MAX_PCT = 5;
export const NULL_IMAGE_MAX_PCT = 50;
export const PLACEHOLDER_TITLE_MAX_PCT = 10;

// title matches "eBay item <numeric-id>"
const PLACEHOLDER_RE = /^ebay item\s+\d+/i;

/**
 * Audit a single JSONL/NDJSON row and update the running tally.
 * @param {object} row  - Parsed JSON object
 * @param {object} tally - Mutable tally object
 */
function tallyRow(row, tally) {
  tally.total++;

  const price = row.price ?? row.sale_price ?? row.current_price ?? null;
  if (price === null || price === '' || Number(price) === 0) {
    tally.zeroPrice++;
  }

  const image = row.image_url ?? row.image ?? row.images ?? null;
  if (!image || (Array.isArray(image) && image.length === 0)) {
    tally.nullImage++;
  }

  const title = (row.title ?? '').trim();
  if (PLACEHOLDER_RE.test(title)) {
    tally.placeholderTitle++;
  }
}

/**
 * Audit a batch from an async iterable of JSONL lines.
 *
 * @param {AsyncIterable<string>} lines
 * @param {string} source   - Human-readable label for error messages
 * @returns {{ pass: boolean, metrics: object, violations: string[] }}
 */
export async function auditBatch(lines, source = 'unknown') {
  const tally = { total: 0, zeroPrice: 0, nullImage: 0, placeholderTitle: 0 };
  let parseErrors = 0;

  for await (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    try {
      tallyRow(JSON.parse(trimmed), tally);
    } catch {
      parseErrors++;
    }
  }

  if (tally.total === 0) {
    return {
      pass: false,
      metrics: { total: 0, parseErrors },
      violations: [`${source}: no rows parsed — cannot validate empty batch`],
    };
  }

  const pct = (n) => (100 * n) / tally.total;
  const metrics = {
    source,
    total: tally.total,
    parseErrors,
    zeroPricePct: pct(tally.zeroPrice),
    nullImagePct: pct(tally.nullImage),
    placeholderTitlePct: pct(tally.placeholderTitle),
  };

  const violations = [];
  if (metrics.zeroPricePct > ZERO_PRICE_MAX_PCT) {
    violations.push(
      `zero_price ${metrics.zeroPricePct.toFixed(1)}% > threshold ${ZERO_PRICE_MAX_PCT}%`
    );
  }
  if (metrics.nullImagePct > NULL_IMAGE_MAX_PCT) {
    violations.push(
      `null_image ${metrics.nullImagePct.toFixed(1)}% > threshold ${NULL_IMAGE_MAX_PCT}%`
    );
  }
  if (metrics.placeholderTitlePct > PLACEHOLDER_TITLE_MAX_PCT) {
    violations.push(
      `placeholder_title ${metrics.placeholderTitlePct.toFixed(1)}% > threshold ${PLACEHOLDER_TITLE_MAX_PCT}%`
    );
  }

  return { pass: violations.length === 0, metrics, violations };
}

/**
 * Assert that the batch passes Checkpoint B.
 * Call this before any INSERT loop.  Throws if the batch is fabricated.
 *
 * @param {AsyncIterable<string>} lines
 * @param {string} source
 * @throws {Error} with human-readable detail on fabrication
 */
export async function assertCheckpointB(lines, source = 'unknown') {
  const result = await auditBatch(lines, source);
  if (!result.pass) {
    const detail = result.violations.join('; ');
    throw new Error(
      `Checkpoint B BLOCKED ingest of "${source}": ${detail}. ` +
      `Re-scrape with a real page scraper before inserting into the catalog.`
    );
  }
  return result.metrics;
}
