#!/usr/bin/env node
/**
 * Hourly throughput dispatcher — v6.4 (BUY-62327)
 *
 * Top of every UTC hour, snapshot pg_stat_all_tables.products and
 * ingestion_runs into canonical_throughput_hourly, compute net products added
 * as delta_ins_from_stats, and file failure child issues on BUY-59639 when
 * throughput < 150K.
 *
 * Canonical DB is read from data/.catalog_db_url (always maglev).
 */

const fs = require('fs');
const path = require('path');
const { Pool } = require('pg');

const REPO_ROOT = path.resolve(__dirname, '..');

const SYNTHETIC_MERCHANTS = [
  'shopnow', 'techdepot', 'fastshop', 'megamart', 'smartcart',
  'valuehub', 'easycart', 'quickbuy', 'primestore', 'globalmart',
];

const TARGET_ROWS_PER_HOUR = 150_000;

const STMT_TIMEOUT_FAST_S = 5;
const STMT_TIMEOUT_FAST_RETRY_S = 20;
const STMT_TIMEOUT_COUNT_S = 30;
const STMT_TIMEOUT_MAX_CREATED_S = 8;

const PARENT_ISSUE_ID = 'be9d4eef-94bc-451e-b574-a620d48a7ffb'; // BUY-59639 canonical v6 dispatcher (current active)
const PASS_COMMENT_ISSUE_ID = 'be9d4eef-94bc-451e-b574-a620d48a7ffb'; // BUY-59639 canonical v6 dispatcher (current active)
const COMPANY_ID = '177bc805-e3c8-4336-84cb-8e1e482d5a17';
const ASSIGNEE_USER_ID = 'MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6';

const CATALOG_DB_URL_FILE = path.join(REPO_ROOT, 'data', '.catalog_db_url');
const STATE_FILE = path.join(REPO_ROOT, 'data', '.throughput_state.json');
const EVIDENCE_DIR = path.join(
  '/paperclip/instances/default/workspaces/',
  'a29ac9dc-cf0a-455b-964c-e75bd2f5fc47/BUY-58452'
);

// ---------------------------------------------------------------------------
// State helpers
// ---------------------------------------------------------------------------

function loadState() {
  try {
    const raw = fs.readFileSync(STATE_FILE, 'utf8');
    return JSON.parse(raw);
  } catch {
    return {};
  }
}

function saveState(state) {
  const dir = path.dirname(STATE_FILE);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  const tmp = STATE_FILE + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(state, null, 2) + '\n', 'utf8');
  fs.renameSync(tmp, STATE_FILE);
}

function parseNullableInt(value) {
  if (value === null || value === undefined) return null;
  const parsed = parseInt(value, 10);
  return Number.isNaN(parsed) ? null : parsed;
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

function apiHeaders() {
  const apiKey = (process.env.PAPERCLIP_API_KEY || '').trim();
  if (!apiKey) return null;
  const h = { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' };
  const runId = jwtRunId(apiKey) || process.env.PAPERCLIP_RUN_ID;
  if (runId) h['X-Paperclip-Run-Id'] = runId;
  return h;
}

function jwtRunId(apiKey) {
  try {
    const payload = apiKey.split('.')[1];
    if (!payload) return null;
    const decoded = JSON.parse(Buffer.from(payload, 'base64url').toString('utf8'));
    return decoded.run_id || null;
  } catch {
    return null;
  }
}

function apiBase() {
  return (process.env.PAPERCLIP_API_URL || 'http://localhost:3000').replace(/\/+$/, '') + '/api';
}

async function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function retryFetch(url, options = {}) {
  const maxAttempts = options.maxAttempts || 3;
  const initialDelay = options.initialDelay || 2000;
  const backoffFactor = options.backoffFactor || 2;
  const maxSleep = options.maxSleep || 20_000;
  let delay = initialDelay;
  let lastError = null;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      const resp = await fetch(url, options);
      if (resp.status === 429) {
        if (attempt === maxAttempts) return resp;
        const retryAfter = resp.headers.get('Retry-After');
        let wait = retryAfter ? parseFloat(retryAfter) * 1000 : delay;
        wait = Math.min(wait, maxSleep);
        console.log(`[retry] attempt ${attempt}/${maxAttempts}: 429; retry in ${wait}ms`);
        await sleep(wait);
        delay = Math.min(delay * backoffFactor, maxSleep);
        continue;
      }
      if (resp.status >= 500 && resp.status < 600) {
        if (attempt === maxAttempts) return resp;
        console.log(`[retry] attempt ${attempt}/${maxAttempts}: HTTP ${resp.status}; retry in ${delay}ms`);
        await sleep(Math.min(delay, maxSleep));
        delay = Math.min(delay * backoffFactor, maxSleep);
        continue;
      }
      return resp;
    } catch (err) {
      lastError = err;
      if (attempt === maxAttempts) throw err;
      console.log(`[retry] attempt ${attempt}/${maxAttempts} failed: ${err.name}: ${err.message}`);
      await sleep(Math.min(delay, maxSleep));
      delay = Math.min(delay * backoffFactor, maxSleep);
    }
  }
  throw lastError || new Error(`exhausted ${maxAttempts} attempts for ${options.method || 'GET'} ${url}`);
}

// ---------------------------------------------------------------------------
// DB helpers
// ---------------------------------------------------------------------------

function readCatalogDbUrl() {
  if (!fs.existsSync(CATALOG_DB_URL_FILE)) {
    throw new Error(`data/.catalog_db_url not found at ${CATALOG_DB_URL_FILE}`);
  }
  const url = fs.readFileSync(CATALOG_DB_URL_FILE, 'utf8').trim();
  if (url.includes('roundhouse')) {
    throw new Error(`data/.catalog_db_url contains roundhouse URL — refusing to use: ${url}`);
  }
  if (!url.includes('maglev')) {
    throw new Error(`data/.catalog_db_url is not maglev — refusing: ${url}`);
  }
  return url;
}

async function withTimeout(client, timeoutSeconds, fn) {
  await client.query(`SET statement_timeout = '${timeoutSeconds}s'`);
  try {
    return await fn(client);
  } finally {
    await client.query('SET statement_timeout = DEFAULT').catch(() => {});
  }
}

async function readPgStatAllProducts(client) {
  let row = null;
  let lastError = null;
  const timeouts = [STMT_TIMEOUT_FAST_S, STMT_TIMEOUT_FAST_RETRY_S];
  for (const timeout of timeouts) {
    try {
      row = await withTimeout(client, timeout, async (c) => {
        const result = await c.query(
          `SELECT n_live_tup, n_tup_ins, n_tup_upd, n_tup_del,
                  seq_scan, idx_scan
           FROM pg_stat_all_tables
           WHERE relname = 'products' AND schemaname = 'public'`
        );
        return result.rows[0];
      });
      if (row) break;
    } catch (err) {
      if (err.code === '57014') {
        lastError = err;
        console.log(`[throughput-dispatcher] pg_stat_all_tables timed out after ${timeout}s`);
          await client.query('ROLLBACK').catch(() => {});
        continue;
      }
      throw err;
    }
  }
  if (!row) {
    if (lastError) throw lastError;
    return null;
  }
  return {
    n_live_tup: parseInt(row.n_live_tup || 0, 10),
    n_tup_ins: parseInt(row.n_tup_ins || 0, 10),
    n_tup_upd: parseInt(row.n_tup_upd || 0, 10),
    n_tup_del: parseInt(row.n_tup_del || 0, 10),
    seq_scan: parseInt(row.seq_scan || 0, 10),
    idx_scan: parseInt(row.idx_scan || 0, 10),
  };
}

async function queryHourWindow(client, hourStart) {
  const hourEnd = new Date(hourStart.getTime() + 60 * 60 * 1000);
  const syntheticList = SYNTHETIC_MERCHANTS.map((m) => `'${m}'`).join(',');
  try {
    const result = await withTimeout(client, STMT_TIMEOUT_COUNT_S, async (c) => {
      return c.query(
        `SELECT
          COUNT(*)::bigint AS total_rows,
          COUNT(*) FILTER (
            WHERE merchant_id::text NOT IN (${syntheticList})
              AND url NOT LIKE '%example.com%'
          )::bigint AS real_rows,
          MIN(created_at) AS first_row,
          MAX(created_at) AS last_row
         FROM products
         WHERE created_at >= $1 AND created_at < $2`,
        [hourStart.toISOString(), hourEnd.toISOString()]
      );
    });
    const row = result.rows[0];
    return {
      total_rows: parseInt(row.total_rows || 0, 10),
      real_rows: parseInt(row.real_rows || 0, 10),
      first_row: row.first_row ? row.first_row.toISOString() : null,
      last_row: row.last_row ? row.last_row.toISOString() : null,
    };
  } catch (err) {
    if (err.code === '57014') {
      await client.query('ROLLBACK').catch(() => {});
      return { error: 'statement_timeout', timeout_s: STMT_TIMEOUT_COUNT_S };
    }
    return { error: 'connection_lost', detail: `${err.name}: ${err.message}` };
  }
}

async function queryMaxCreatedAt(client) {
  try {
    const result = await withTimeout(client, STMT_TIMEOUT_MAX_CREATED_S, async (c) => {
      return c.query('SELECT MAX(created_at) FROM products');
    });
    return { max_created_at: result.rows[0].max ? result.rows[0].max.toISOString() : null };
  } catch (err) {
    if (err.code === '57014') {
      await client.query('ROLLBACK').catch(() => {});
      return { error: 'statement_timeout', timeout_s: STMT_TIMEOUT_MAX_CREATED_S };
    }
    return { error: 'connection_lost', detail: `${err.name}: ${err.message}` };
  }
}

async function queryPostmasterStartTime(client) {
  try {
    const result = await withTimeout(client, STMT_TIMEOUT_FAST_S, async (c) => {
      return c.query('SELECT pg_postmaster_start_time()');
    });
    return result.rows[0].pg_postmaster_start_time
      ? result.rows[0].pg_postmaster_start_time.toISOString()
      : null;
  } catch {
    return null;
  }
}

async function upsertCanonicalThroughputRow(client, hourStart, stat, pmStart, hourData, source, note) {
  const hourStartTs = new Date(Date.UTC(hourStart.getUTCFullYear(), hourStart.getUTCMonth(), hourStart.getUTCDate(), hourStart.getUTCHours()));
  const hourEndTs = new Date(hourStartTs.getTime() + 60 * 60 * 1000);
  const nTupIns = stat.n_tup_ins;
  const nTupUpd = stat.n_tup_upd;
  const nLiveTup = stat.n_live_tup;

  // Best-effort live_count
  let liveCount = null;
  try {
    const r = await withTimeout(client, 3, async (c) => {
      return c.query('SELECT count(*)::bigint FROM products');
    });
    liveCount = parseInt(r.rows[0].count || 0, 10);
  } catch {
    // ignore
  }

  // ingestion_runs aggregates for the hour
  let ingRuns = 0;
  let ingInserted = 0;
  let ingUpdated = 0;
  try {
    const r = await withTimeout(client, 5, async (c) => {
      return c.query(
        `SELECT count(*)::int AS runs,
                COALESCE(sum(rows_inserted), 0)::bigint AS ins,
                COALESCE(sum(rows_updated), 0)::bigint AS upd
         FROM ingestion_runs
         WHERE started_at >= $1 AND started_at < $2
           AND status = 'completed'`,
        [hourStartTs.toISOString(), hourEndTs.toISOString()]
      );
    });
    ingRuns = parseInt(r.rows[0].runs || 0, 10);
    ingInserted = parseInt(r.rows[0].ins || 0, 10);
    ingUpdated = parseInt(r.rows[0].upd || 0, 10);
  } catch {
    // ignore
  }

  // Compute delta against the immediately-previous hour
  let deltaInsFromStats = null;
  let deltaUpdFromStats = null;
  let statResetDetected = null;
  let previousNTupIns = null;
  let previousNTupUpd = null;
  try {
    const r = await withTimeout(client, 10, async (c) => {
      return c.query(
        `SELECT n_tup_ins, n_tup_upd
         FROM canonical_throughput_hourly
         WHERE hour_start = $1::timestamptz - INTERVAL '1 hour'`,
        [hourStartTs.toISOString()]
      );
    });
    const prv = r.rows[0];
    if (prv) {
      previousNTupIns = parseNullableInt(prv.n_tup_ins);
      previousNTupUpd = parseNullableInt(prv.n_tup_upd);
      if (nTupIns != null && previousNTupIns != null) {
        if (previousNTupIns > nTupIns || previousNTupIns === 0) {
          statResetDetected = true;
        } else {
          statResetDetected = false;
          deltaInsFromStats = nTupIns - previousNTupIns;
          deltaUpdFromStats = nTupUpd - previousNTupUpd;
        }
      }
    }
  } catch {
    // ignore
  }

  // If the row already exists, preserve the original n_tup_ins/n_tup_upd snapshots
  // and deltas so a late refresh doesn't overwrite a real reading with the current
  // absolute counter. We only overwrite if this is the first write for the hour.
  let existingNTupIns = null;
  let existingNTupUpd = null;
  let existingDeltaIns = null;
  let existingDeltaUpd = null;
  let existingStatReset = null;
  try {
    const r = await withTimeout(client, 10, async (c) => {
      return c.query('SELECT n_tup_ins, n_tup_upd, delta_ins_from_stats, delta_upd_from_stats, stat_reset_detected FROM canonical_throughput_hourly WHERE hour_start = $1', [hourStartTs.toISOString()]);
    });
    const existing = r.rows[0];
    if (existing) {
      existingNTupIns = parseNullableInt(existing.n_tup_ins);
      existingNTupUpd = parseNullableInt(existing.n_tup_upd);
      existingDeltaIns = parseNullableInt(existing.delta_ins_from_stats);
      existingDeltaUpd = parseNullableInt(existing.delta_upd_from_stats);
      existingStatReset = existing.stat_reset_detected;
    }
  } catch {
    // ignore
  }

  const nTupInsSnap = existingNTupIns != null ? existingNTupIns : nTupIns;
  const nTupUpdSnap = existingNTupUpd != null ? existingNTupUpd : nTupUpd;
  if (existingDeltaIns != null) deltaInsFromStats = existingDeltaIns;
  if (existingDeltaUpd != null) deltaUpdFromStats = existingDeltaUpd;
  if (existingStatReset != null) statResetDetected = existingStatReset;

  try {
    const r = await withTimeout(client, 5, async (c) => {
      return c.query(
        `INSERT INTO canonical_throughput_hourly
          (hour_start, n_tup_ins, n_tup_upd, n_live_tup, live_count,
           ing_runs, ing_inserted, ing_updated, pm_start, source, note,
           delta_ins_from_stats, delta_upd_from_stats,
           stat_reset_detected, delta_computed_at)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11,
                 $12, $13, $14, now())
         ON CONFLICT (hour_start) DO UPDATE SET
           n_live_tup  = EXCLUDED.n_live_tup,
           live_count  = EXCLUDED.live_count,
           ing_runs    = EXCLUDED.ing_runs,
           ing_inserted= EXCLUDED.ing_inserted,
           ing_updated = EXCLUDED.ing_updated,
           pm_start    = EXCLUDED.pm_start,
           source      = EXCLUDED.source,
           note        = EXCLUDED.note,
           delta_ins_from_stats = EXCLUDED.delta_ins_from_stats,
           delta_upd_from_stats = EXCLUDED.delta_upd_from_stats,
           stat_reset_detected  = EXCLUDED.stat_reset_detected,
           delta_computed_at    = EXCLUDED.delta_computed_at,
           recorded_at = now()
         RETURNING hour_start`,
        [hourStartTs.toISOString(), nTupInsSnap, nTupUpdSnap, nLiveTup, liveCount,
         ingRuns, ingInserted, ingUpdated, pmStart, source, note,
         deltaInsFromStats, deltaUpdFromStats, statResetDetected]
      );
    });
    return {
      upserted: r.rows.length > 0,
      hour_start: hourStartTs.toISOString(),
      live_count: liveCount,
      ing_runs: ingRuns,
      ing_inserted: ingInserted,
      delta_ins_from_stats: deltaInsFromStats,
      delta_upd_from_stats: deltaUpdFromStats,
      stat_reset_detected: statResetDetected,
      n_tup_ins: nTupInsSnap,
      n_tup_upd: nTupUpdSnap,
      previous_n_tup_ins: previousNTupIns,
      previous_n_tup_upd: previousNTupUpd,
      n_live_tup: nLiveTup,
      note: 'upserted',
    };
  } catch (err) {
    if (err.code === '57014') {
      return { upserted: false, hour_start: hourStartTs.toISOString(), note: 'upsert timeout' };
    }
    return { upserted: false, hour_start: hourStartTs.toISOString(), note: `upsert error: ${err.message}` };
  }
}

// ---------------------------------------------------------------------------
// v6 decision logic
// ---------------------------------------------------------------------------

function selectV6ThroughputSignal(deltaInsFromStats, canonicalIngInserted, liveCountDelta, nLiveTupDelta) {
  // nLiveTupGuardBlockedByIngInserted: only for fallback case when delta_ins_from_stats is NULL
  const nLiveTupGuardBlockedByIngInserted =
    nLiveTupDelta != null &&
    nLiveTupDelta >= TARGET_ROWS_PER_HOUR &&
    canonicalIngInserted != null &&
    canonicalIngInserted < TARGET_ROWS_PER_HOUR;

  // v6.4: When delta_ins_from_stats is non-null and below target, use n_live_tup_delta guard if >= 150K
  // UNLESS ing_inserted corroboration blocks it (autovacuum bloat release detected)
  if (
    deltaInsFromStats != null &&
    deltaInsFromStats < TARGET_ROWS_PER_HOUR &&
    nLiveTupDelta != null &&
    nLiveTupDelta >= TARGET_ROWS_PER_HOUR &&
    !nLiveTupGuardBlockedByIngInserted
  ) {
    return [nLiveTupDelta, 'n_live_tup_delta_guard'];
  }

  if (deltaInsFromStats != null) {
    return [deltaInsFromStats, 'delta_ins_from_stats'];
  }

  // Fallback case: delta_ins_from_stats is NULL - ing_inserted blocking applies here
  if (
    nLiveTupDelta != null &&
    nLiveTupDelta >= TARGET_ROWS_PER_HOUR &&
    !nLiveTupGuardBlockedByIngInserted
  ) {
    return [nLiveTupDelta, 'n_live_tup_delta_guard'];
  }

  if (liveCountDelta != null && liveCountDelta >= TARGET_ROWS_PER_HOUR) {
    return [liveCountDelta, 'live_count_delta'];
  }

  const ingInserted = canonicalIngInserted || 0;
  if (ingInserted > 0) {
    return [ingInserted, 'ingestion_runs_observability'];
  }

  if (liveCountDelta != null) {
    return [liveCountDelta, 'live_count_delta'];
  }
  return [0, 'unavailable'];
}

function shouldFileV6FailureTicket(deltaInsFromStats, canonicalIngInserted, liveCountDelta, nLiveTupDelta) {
  // When delta_ins_from_stats is non-null and below target, use n_live_tup_delta guard if >= 150K
  // (ing_inserted is observability-only when delta_ins_from_stats is available)
  if (deltaInsFromStats != null) {
    if (deltaInsFromStats >= TARGET_ROWS_PER_HOUR) {
      return false;
    }
    if (
      nLiveTupDelta != null &&
      nLiveTupDelta >= TARGET_ROWS_PER_HOUR &&
      !(canonicalIngInserted != null && canonicalIngInserted < TARGET_ROWS_PER_HOUR)
    ) {
      return false;
    }
    if (liveCountDelta != null && liveCountDelta >= TARGET_ROWS_PER_HOUR) {
      return false;
    }
    return true;
  }

  const nLiveTupGuardBlockedByIngInserted =
    nLiveTupDelta != null &&
    nLiveTupDelta >= TARGET_ROWS_PER_HOUR &&
    canonicalIngInserted != null &&
    canonicalIngInserted < TARGET_ROWS_PER_HOUR;

  if (
    nLiveTupDelta != null &&
    nLiveTupDelta >= TARGET_ROWS_PER_HOUR &&
    !nLiveTupGuardBlockedByIngInserted
  ) {
    return false;
  }
  if (liveCountDelta != null && liveCountDelta >= TARGET_ROWS_PER_HOUR) {
    return false;
  }
  const ingestionUnavailableOrLow = canonicalIngInserted === null || canonicalIngInserted < TARGET_ROWS_PER_HOUR;
  const liveCountUnavailableOrLow = liveCountDelta === null || liveCountDelta < TARGET_ROWS_PER_HOUR;
  return ingestionUnavailableOrLow && liveCountUnavailableOrLow;
}

function assertV6ForbiddenPatterns({
  deltaInsFromStats,
  deltaUpdFromStats,
  realRows,
  source,
  liveCountDelta,
  currentNTupIns,
  previousNTupIns,
}) {
  // Rule 6(c)
  if (
    deltaInsFromStats != null &&
    deltaInsFromStats === 0 &&
    currentNTupIns != null &&
    previousNTupIns != null &&
    currentNTupIns !== previousNTupIns
  ) {
    throw new Error(
      `v6 rule 6(c) violation: delta_ins_from_stats=0 while raw consecutive n_tup_ins values differ (${previousNTupIns} -> ${currentNTupIns}). Investigate canonical_throughput_hourly upsert; do NOT file a FAIL ticket.`
    );
  }
  // Rule 6(a)
  if (
    deltaInsFromStats != null &&
    realRows < TARGET_ROWS_PER_HOUR &&
    source === 'ingestion_runs_observability'
  ) {
    throw new Error(
      'v6 rule 6(a) violation: source fell back to ingestion_runs while delta_ins_from_stats is non-null. ingestion_runs is observability-only; real_rows must equal delta_ins_from_stats when available.'
    );
  }
  // Rule 6(b)
  if (
    deltaInsFromStats != null &&
    deltaInsFromStats > 0 &&
    liveCountDelta != null &&
    liveCountDelta === 0 &&
    realRows < TARGET_ROWS_PER_HOUR &&
    source === 'live_count_delta'
  ) {
    throw new Error(
      `v6 rule 6(b) violation: live_count_delta=0 while delta_ins_from_stats=+${deltaInsFromStats}. Do NOT file a FAIL ticket.`
    );
  }
  if (
    liveCountDelta != null &&
    liveCountDelta > 0 &&
    deltaInsFromStats != null &&
    deltaInsFromStats === 0 &&
    realRows < TARGET_ROWS_PER_HOUR &&
    source === 'delta_ins_from_stats'
  ) {
    throw new Error(
      `v6 rule 6(b) violation: delta_ins_from_stats=0 while live_count_delta=+${liveCountDelta}. Do NOT file a FAIL ticket.`
    );
  }
}

// ---------------------------------------------------------------------------
// Issue lifecycle helpers
// ---------------------------------------------------------------------------

async function dedupCheckExistingChild(hourStart) {
  const headers = apiHeaders();
  if (!headers) return false;
  const end = new Date(hourStart.getTime() + 60 * 60 * 1000);
  const dateTag = `${hourStart.getUTCFullYear()}-${pad2(hourStart.getUTCMonth() + 1)}-${pad2(hourStart.getUTCDate())}`;
  const windowTag = `${dateTag} ${pad2(hourStart.getUTCHours())}:${pad2(hourStart.getUTCMinutes())} UTC fire, ${pad2(hourStart.getUTCHours())}:${pad2(hourStart.getUTCMinutes())}–${pad2(end.getUTCHours())}:${pad2(end.getUTCMinutes())} window)`;
  const fallbackTag = `${pad2(hourStart.getUTCHours())}:${pad2(hourStart.getUTCMinutes())}–${pad2(end.getUTCHours())}:${pad2(end.getUTCMinutes())} window)`;
  try {
    const url = new URL(`${apiBase()}/companies/${COMPANY_ID}/issues`);
    url.searchParams.set('parentId', PARENT_ISSUE_ID);
    url.searchParams.set('limit', '100');
    url.searchParams.set('status', 'todo,in_progress');
    const resp = await retryFetch(url.toString(), { headers, method: 'GET' });
    if (!resp.ok) {
      console.log(`[throughput-dispatcher] dedup_check_existing_child: GET ${resp.status} — skipping`);
      return false;
    }
    const body = await resp.json();
    const issues = Array.isArray(body) ? body : body.issues || [];
    return issues.some((issue) => {
      if (!issue.title) return false;
      if (issue.title.includes(windowTag)) return true;
      return issue.title.includes(dateTag) && issue.title.includes(fallbackTag);
    });
  } catch (err) {
    console.log(`[throughput-dispatcher] dedup_check_existing_child: ${err.name}: ${err.message}`);
    return false;
  }
}

async function retryPendingChildren(state) {
  const pending = state.pending_children || [];
  if (!pending.length) return [];
  const headers = apiHeaders();
  if (!headers) {
    console.log('[throughput-dispatcher] RETRY: no API key; leaving pending children');
    return [];
  }
  const remaining = [];
  const filed = [];
  for (const entry of pending) {
    const hs = entry.hour_start_iso ? new Date(entry.hour_start_iso) : null;
    try {
      const ident = await createStallIssue(
        hs, entry.real_rows, entry.source, entry.note,
        entry.hour_data, entry.stat, entry.max_created, entry.db_host, entry.fire_ts
      );
      filed.push(ident);
      console.log(`[throughput-dispatcher] RETRY filed pending child ${ident} for ${hs ? hs.toISOString() : 'unknown'}`);
    } catch (err) {
      remaining.push(entry);
      console.log(`[throughput-dispatcher] RETRY failed: ${err.name}: ${err.message}`);
    }
  }
  state.pending_children = remaining;
  return filed;
}

async function createStallIssue(hourStart, realRows, source, note, hourData, stat, maxCreated, dbHost, fireTs) {
  const description = buildEvidenceMarkdown(hourStart, realRows, source, note, hourData, stat, maxCreated, dbHost, fireTs);
  const hourEnd = new Date(hourStart.getTime() + 60 * 60 * 1000);
  const title =
    `[BUY-59639 dispatcher] Hourly throughput check ` +
    `(${hourStart.getUTCFullYear()}-${pad2(hourStart.getUTCMonth() + 1)}-${pad2(hourStart.getUTCDate())} ${pad2(hourStart.getUTCHours())}:${pad2(hourStart.getUTCMinutes())} UTC fire, ` +
    `${pad2(hourStart.getUTCHours())}:${pad2(hourStart.getUTCMinutes())}–` +
    `${pad2(hourEnd.getUTCHours())}:${pad2(hourEnd.getUTCMinutes())} window)`;

  const payload = {
    companyId: COMPANY_ID,
    title,
    description,
    parentId: PARENT_ISSUE_ID,
    status: 'todo',
    priority: 'high',
    assigneeUserId: ASSIGNEE_USER_ID,
  };
  const headers = apiHeaders();
  if (!headers) throw new Error('missing PAPERCLIP_API_KEY; cannot file child issue');

  const resp = await retryFetch(`${apiBase()}/companies/${COMPANY_ID}/issues`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
    const text = await resp.text().catch(() => '');
    throw new Error(`createStallIssue POST ${resp.status}: ${text}`);
  }
  const body = await resp.json();
  const identifier = body.identifier || 'BUY-????';
  const issueId = body.id;

  if (issueId) {
    const vr = await retryFetch(`${apiBase()}/issues/${issueId}`, { headers, method: 'GET' });
    if (!vr.ok) {
      throw new Error(`createStallIssue: verification GET returned ${vr.status}; cannot confirm ${identifier} persisted`);
    }
    const vbody = await vr.json();
    if (vbody.id !== issueId || vbody.identifier !== identifier) {
      throw new Error(`createStallIssue: silent rollback detected for ${identifier}`);
    }
  }
  return identifier;
}

function buildEvidenceMarkdown(hourStart, realRows, source, note, hourData, stat, maxCreated, dbHost, fireTs) {
  const hourEnd = new Date(hourStart.getTime() + 60 * 60 * 1000);
  const pct = (100.0 * realRows) / TARGET_ROWS_PER_HOUR;
  const margin = realRows - TARGET_ROWS_PER_HOUR;
  const hourLabel = formatISO8601NoMs(hourStart);

  let countBlock = '| (skipped — fast-path only) |';
  if (hourData) {
    if (hourData.error) {
      countBlock = `| (timeout after ${hourData.timeout_s}s — fast-path only) |`;
    } else {
      countBlock =
        `| ${hourData.total_rows.toLocaleString()} | ${hourData.real_rows.toLocaleString()} | ` +
        `${hourData.first_row || '(none)'} | ${hourData.last_row || '(none)'} |`;
    }
  }

  const maxBlock =
    maxCreated && maxCreated.max_created_at
      ? `| ${maxCreated.max_created_at} |`
      : '| (timeout — staleness inferred from n_tup_ins delta) |';

  return `# Hourly Throughput Check — ${hourLabel}

**Result: ${realRows >= TARGET_ROWS_PER_HOUR ? 'PASS' : 'FAIL'} — ${realRows.toLocaleString()} / ${TARGET_ROWS_PER_HOUR.toLocaleString()} (${pct.toFixed(1)}%).**

Parent: [BUY-59639](/BUY/issues/BUY-59639). Dispatcher: [BUY-59639](/BUY/issues/BUY-59639). Source: \`${source}\`.

> ${note}

## Just-completed hour: ${hourStart.toISOString()} → ${hourEnd.toISOString()}

| Metric | Value |
|---|---|
| Real rows (per \`${source}\`) | **${realRows.toLocaleString()}** |
| Threshold | ${TARGET_ROWS_PER_HOUR.toLocaleString()} |
| Margin vs. threshold | **${margin > 0 ? '+' : ''}${margin.toLocaleString()} (${(pct - 100).toFixed(1)}%)** |
| % of 150,000/hr target | **${pct.toFixed(1)}%** |
| \`pg_stat_all_tables.products.n_live_tup\` | ${stat && stat.n_live_tup != null ? stat.n_live_tup.toLocaleString() : '?'} |
| \`pg_stat_all_tables.products.n_tup_ins\`  | ${stat && stat.n_tup_ins != null ? stat.n_tup_ins.toLocaleString() : '?'} |
| \`MAX(created_at)\` (snapshot ${fireTs}) ${maxBlock} |

## Hour-bucket COUNT verification (best-effort)

| total_rows | real_rows | first_row | last_row |
|---:|---:|---|---|
${countBlock}

## DB proof (canonical PostgreSQL @ ${dbHost})

Connection string source: \`data/.catalog_db_url\` (maglev). NOT the harness \`DATABASE_URL\`.

- n_tup_ins delta query:
  \`\`\`sql
  SELECT n_live_tup, n_tup_ins, n_tup_upd
  FROM pg_stat_all_tables WHERE schemaname = 'public' AND relname = 'products';
  -- ${stat && stat.n_live_tup != null ? stat.n_live_tup.toLocaleString() : '?'} | ${stat && stat.n_tup_ins != null ? stat.n_tup_ins.toLocaleString() : '?'} | ${stat && stat.n_tup_upd != null ? stat.n_tup_upd.toLocaleString() : '?'}
  \`\`\`
- Hour-bucket COUNT:
  \`\`\`sql
  SELECT date_trunc('hour', created_at) AS hour, COUNT(*) AS rows
  FROM products
  WHERE created_at >= '${hourStart.toISOString()}'
    AND created_at <  '${hourEnd.toISOString()}'
  GROUP BY 1 ORDER BY 1;
  \`\`\`
`;
}

async function writeEvidenceMarkdown(hourStart, realRows, source, note, hourData, stat, maxCreated, dbHost, fireTs, failureChildIdentifier) {
  try {
    if (!fs.existsSync(EVIDENCE_DIR)) {
      fs.mkdirSync(EVIDENCE_DIR, { recursive: true });
    }
    let md = buildEvidenceMarkdown(hourStart, realRows, source, note, hourData, stat, maxCreated, dbHost, fireTs);
    if (failureChildIdentifier) {
      md += `\n\nFailure child: [${failureChildIdentifier}](/BUY/issues/${failureChildIdentifier})\n`;
    }
    const hourLabel = formatISO8601NoMs(hourStart);
    const filePath = path.join(EVIDENCE_DIR, `hourly-throughput-${hourLabel}Z.md`);
    fs.writeFileSync(filePath, md, 'utf8');
    console.log(`[throughput-dispatcher] evidence markdown written: ${filePath}`);
    return filePath;
  } catch (err) {
    console.log(`[throughput-dispatcher] WARNING: failed to write evidence markdown: ${err.name}: ${err.message}`);
    return null;
  }
}

async function postParentPassComment(hourStart, realRows, source) {
  const headers = apiHeaders();
  if (!headers) {
    console.log('[throughput-dispatcher] WARNING: no API key; skipping PASS comment');
    return;
  }
  const hourEnd = new Date(hourStart.getTime() + 60 * 60 * 1000);
  const body =
    `PASS — ${realRows.toLocaleString()} products added in ` +
    `${pad2(hourStart.getUTCHours())}:${pad2(hourStart.getUTCMinutes())}–` +
    `${pad2(hourEnd.getUTCHours())}:${pad2(hourEnd.getUTCMinutes())} UTC ` +
    `${hourStart.toISOString().slice(0, 10)} (source=${source}, target=150,000).`;
  try {
    const resp = await retryFetch(`${apiBase()}/issues/${PASS_COMMENT_ISSUE_ID}/comments`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ body }),
    });
    if (resp.ok) {
      console.log('[throughput-dispatcher] PASS comment posted on BUY-59639');
    } else {
      console.log(`[throughput-dispatcher] WARNING: PASS comment POST ${resp.status}`);
    }
  } catch (err) {
    console.log(`[throughput-dispatcher] WARNING: PASS comment failed: ${err.name}: ${err.message}`);
  }
}

function buildRunNote({ hourStart, hourEnd, result, realRows, source, deltaRows, stat, pmStart, failureIdentifier, statResetDetected, liveCountDelta, nLiveTupDelta }) {
  const parts = [
    `${formatISO8601NoMs(hourStart)} ${pad2(hourStart.getUTCHours())}:${pad2(hourStart.getUTCMinutes())}-${pad2(hourEnd.getUTCHours())}:${pad2(hourEnd.getUTCMinutes())}Z hour ${result}: ${realRows.toLocaleString()}/hr via ${source}.`,
  ];
  if (deltaRows != null) parts.push(`n_tup_ins delta ${deltaRows.toLocaleString()} over 1.000h = ${realRows.toLocaleString()}/hr.`);
  else parts.push('n_tup_ins delta unavailable.');
  if (statResetDetected) parts.push('stat_reset_detected=True.');
  if (liveCountDelta != null) parts.push(`live_count delta ${liveCountDelta.toLocaleString()}.`);
  if (nLiveTupDelta != null) parts.push(`n_live_tup delta ${nLiveTupDelta.toLocaleString()}.`);
  parts.push(`n_tup_ins=${stat && stat.n_tup_ins != null ? stat.n_tup_ins.toLocaleString() : 0}, n_live_tup=${stat && stat.n_live_tup != null ? stat.n_live_tup.toLocaleString() : 0}.`);
  if (pmStart) parts.push(`pm_start=${pmStart}.`);
  if (failureIdentifier) parts.push(`Filed child ${failureIdentifier} under BUY-59639.`);
  else parts.push('No child filed.');
  return parts.join(' ');
}

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------

function pad2(n) {
  return String(n).padStart(2, '0');
}

function formatISO8601NoMs(d) {
  return `${d.getUTCFullYear()}-${pad2(d.getUTCMonth() + 1)}-${pad2(d.getUTCDate())}T${pad2(d.getUTCHours())}`;
}

function toPythonIsoString(d) {
  const ms = String(d.getUTCMilliseconds()).padStart(3, '0');
  return `${d.getUTCFullYear()}-${pad2(d.getUTCMonth() + 1)}-${pad2(d.getUTCDate())}T${pad2(d.getUTCHours())}:${pad2(d.getUTCMinutes())}:${pad2(d.getUTCSeconds())}.${ms}+00:00`;
}

function parseHourString(s) {
  return new Date(s.replace(/\+00:00$/, 'Z'));
}

function parseHourStart(str) {
  // Accept 2026-07-13T17:00 or 2026-07-13T17:00:00Z etc.
  const s = str.replace('Z', '+00:00');
  const d = new Date(s);
  if (isNaN(d.getTime())) throw new Error(`Invalid --check-hour: ${str}`);
  return new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate(), d.getUTCHours()));
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------


/**
 * Return true only when the entire hourly window has elapsed.
 * Python parity: hourly_throughput_dispatcher.is_completed_hour
 */
function isCompletedHour(hourStart, now) {
  // Normalize both to the top of their UTC hour
  const hs = new Date(Date.UTC(
    hourStart.getUTCFullYear(),
    hourStart.getUTCMonth(),
    hourStart.getUTCDate(),
    hourStart.getUTCHours(),
  ));
  return (hs.getTime() + 60 * 60 * 1000) <= now.getTime();
}
async function main() {
  const args = process.argv.slice(2);
  const dryRun = args.includes('--dry-run');
  const force = args.includes('--force');
  const checkHourIdx = args.indexOf('--check-hour');
  const checkHour = checkHourIdx >= 0 ? args[checkHourIdx + 1] : null;

  const now = new Date();
  let hourStart;
  if (checkHour) {
    hourStart = parseHourStart(checkHour);
  } else {
    hourStart = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), now.getUTCHours() - 1));
  }
  const fireTs = `${now.toISOString().slice(0, 16).replace('T', ' ')} UTC`;
  const hourEnd = new Date(hourStart.getTime() + 60 * 60 * 1000);

  if (checkHour && !isCompletedHour(hourStart, now)) {
    console.log(`ERROR: --check-hour must target a completed UTC hour (got ${hourStart.toISOString()} → ${hourEnd.toISOString()}, now=${now.toISOString()})`);
    return 2;
  }

  console.log(`[throughput-dispatcher] Checking hour ${hourStart.toISOString()} → ${hourEnd.toISOString()}`);

  const dbUrl = readCatalogDbUrl();
  const dbUrlObj = new URL(dbUrl);
  const dbHost = `${dbUrlObj.hostname}:${dbUrlObj.port}${dbUrlObj.pathname}`;
  console.log(`[throughput-dispatcher] DB: ${dbHost}`);
  const pool = new Pool({
    user: dbUrlObj.username,
    password: dbUrlObj.password,
    host: dbUrlObj.hostname,
    port: parseInt(dbUrlObj.port || 5432, 10),
    database: dbUrlObj.pathname.replace(/^\//, ''),
    max: 2,
    connectionTimeoutMillis: 15000,
    ssl: { rejectUnauthorized: false },
  });
  let client;
  let state = loadState();
  let failureIdentifier = null;

  try {
    // Retry pending children before current hour
    if (!dryRun) {
      const retried = await retryPendingChildren(state);
      if (retried.length) {
        console.log(`[throughput-dispatcher] RETRY filed ${retried.length} previously-buffered children: ${retried.join(', ')}`);
        state.last_failure_child_identifier = retried[retried.length - 1];
      }
      if (state.pending_children && state.pending_children.length) {
        console.log(`[throughput-dispatcher] RETRY still pending: ${state.pending_children.length} child(ren) remain`);
      }
      saveState(state);
    }

    // Dedup
    if (!force && state.last_hour_checked && parseHourString(state.last_hour_checked).getTime() === hourStart.getTime()) {
      console.log(`[throughput-dispatcher] Already ran for ${hourStart.toISOString()}, skipping (use --force to override).`);
      return 0;
    }

    if (!dryRun && await dedupCheckExistingChild(hourStart)) {
      console.log(`[throughput-dispatcher] Child issue already exists for ${hourStart.toISOString()}, skipping.`);
      return 0;
    }


    client = await pool.connect();

    // Primary: pg_stat_all_tables
    const stat = await readPgStatAllProducts(client);
    if (!stat) {
      console.log('[throughput-dispatcher] FATAL: pg_stat_all_tables returned no row for products');
      return 2;
    }

    // Secondary: hour-bucket COUNT (best-effort)
    const hourData = await queryHourWindow(client, hourStart);
    if (hourData && !hourData.error) {
      console.log(`[throughput-dispatcher] hour_bucket_count: total=${hourData.total_rows.toLocaleString()} real=${hourData.real_rows.toLocaleString()}`);
    } else if (hourData && hourData.error === 'statement_timeout') {
      console.log(`[throughput-dispatcher] hour_bucket_count: TIMEOUT after ${hourData.timeout_s}s (maglev contention — using n_tup_ins delta only)`);
    } else if (hourData && hourData.error === 'connection_lost') {
      console.log('[throughput-dispatcher] hour_bucket_count: connection lost during COUNT');
    } else {
      console.log('[throughput-dispatcher] hour_bucket_count: returned None');
    }

    // Staleness snapshot
    const maxCreated = await queryMaxCreatedAt(client);
    const pmStart = await queryPostmasterStartTime(client);

    // Canonical upsert
    let canonicalUpsert = {};
    try {
      canonicalUpsert = await upsertCanonicalThroughputRow(client, hourStart, stat, pmStart, hourData, 'v6', 'v6.4 JS decision layer active');
      if (canonicalUpsert.upserted) {
        console.log(`[throughput-dispatcher] canonical_throughput_hourly upserted for hour_start=${canonicalUpsert.hour_start} (live_count=${canonicalUpsert.live_count}, ing_inserted=${canonicalUpsert.ing_inserted})`);
      } else {
        console.log(`[throughput-dispatcher] canonical_throughput_hourly upsert skipped: ${canonicalUpsert.note}`);
      }
    } catch (err) {
      console.log(`[throughput-dispatcher] canonical_throughput_hourly upsert raised: ${err.name}: ${err.message}`);
    }

    // v6 decision layer
    let deltaInsFromStats = canonicalUpsert.delta_ins_from_stats;
    let deltaUpdFromStats = canonicalUpsert.delta_upd_from_stats;
    let statResetDetected = canonicalUpsert.stat_reset_detected;
    let canonicalIngInserted = canonicalUpsert.ing_inserted == null ? null : canonicalUpsert.ing_inserted;
    let previousNTupIns = canonicalUpsert.previous_n_tup_ins;

    // Missing prior baseline detection
    let missingPriorBaseline = false;
    if (
      canonicalUpsert.upserted &&
      previousNTupIns == null &&
      canonicalUpsert.n_tup_ins != null &&
      deltaInsFromStats === canonicalUpsert.n_tup_ins
    ) {
      missingPriorBaseline = true;
      deltaInsFromStats = null;
      deltaUpdFromStats = null;
      statResetDetected = null;
      console.log('[throughput-dispatcher] canonical baseline only: missing immediate prior hour row; ignoring absolute n_tup_ins counter for this decision');
    }

    // live_count delta from canonical table
    let liveCountDelta = null;
    if (canonicalUpsert.upserted) {
      try {
        const r = await withTimeout(client, 10, async (c) => {
             return c.query(
               `SELECT live_count FROM canonical_throughput_hourly
             WHERE hour_start = $1::timestamptz - INTERVAL '1 hour'`,
            [hourStart.toISOString()]
          );
        });
        const prv = r.rows[0];
        if (prv && canonicalUpsert.live_count != null && prv.live_count != null) {
          liveCountDelta = canonicalUpsert.live_count - parseInt(prv.live_count, 10);
        }
      } catch {
        // ignore
      }
    }

    // n_live_tup delta from canonical table
    let nLiveTupDelta = null;
    if (canonicalUpsert.upserted) {
      try {
        const r = await withTimeout(client, 10, async (c) => {
             return c.query(
               `SELECT n_live_tup, n_tup_ins FROM canonical_throughput_hourly
             WHERE hour_start = $1::timestamptz - INTERVAL '1 hour'`,
            [hourStart.toISOString()]
          );
        });
        const prv = r.rows[0];
        const curNlt = canonicalUpsert.n_live_tup;
        if (prv && curNlt != null && prv.n_live_tup != null) {
          nLiveTupDelta = parseInt(curNlt, 10) - parseInt(prv.n_live_tup, 10);
        }
        if (previousNTupIns == null && prv && prv.n_tup_ins != null) {
          previousNTupIns = parseInt(prv.n_tup_ins, 10);
        }
      } catch {
        // ignore
      }
    }

    const [realRows, source] = selectV6ThroughputSignal(deltaInsFromStats, canonicalIngInserted, liveCountDelta, nLiveTupDelta);
    const note = `v6.4 metric: source=${source}, delta_ins=${deltaInsFromStats}, live_count_delta=${liveCountDelta}, n_live_tup_delta=${nLiveTupDelta}`;

    // Forbidden-pattern assertions
    assertV6ForbiddenPatterns({
      deltaInsFromStats,
      deltaUpdFromStats,
      realRows,
      source,
      liveCountDelta,
      currentNTupIns: canonicalUpsert.n_tup_ins,
      previousNTupIns,
    });

    console.log(`[throughput-dispatcher] real_rows=${realRows.toLocaleString()} target=${TARGET_ROWS_PER_HOUR.toLocaleString()} (${(100.0 * realRows / TARGET_ROWS_PER_HOUR).toFixed(1)}%) source=${source}`);

    const isFirstBaseline = !state.last_n_tup_ins && deltaInsFromStats == null && liveCountDelta == null;
    const shouldFileFailure = shouldFileV6FailureTicket(deltaInsFromStats, canonicalIngInserted, liveCountDelta, nLiveTupDelta);

    if (dryRun) {
      console.log('[throughput-dispatcher] --dry-run: would NOT call the Paperclip API');
      if (isFirstBaseline) {
        console.log('  BASELINE_CAPTURE: persisting n_tup_ins as the first reading; no issue filed this run.');
      } else if (source === 'unavailable') {
        console.log('  SKIP: no reliable throughput signal available this hour; no issue would be filed.');
      } else {
        console.log(`  PASS=${!shouldFileFailure} → ${shouldFileFailure ? 'would file under BUY-59639' : 'no-op'}`);
      }
    } else {
      if (isFirstBaseline) {
        console.log('[throughput-dispatcher] BASELINE_CAPTURE: no prior n_tup_ins reading — persisting baseline and skipping the file/no-file decision.');
      } else if (source === 'unavailable') {
        console.log('[throughput-dispatcher] SKIP: throughput signal unavailable; persisting baseline only.');
      } else if (shouldFileFailure && realRows < TARGET_ROWS_PER_HOUR && !force) {
        try {
          failureIdentifier = await createStallIssue(hourStart, realRows, source, note, hourData, stat, maxCreated, dbHost, fireTs);
          console.log(`[throughput-dispatcher] FAIL — filed ${failureIdentifier} under BUY-59639`);
          await writeEvidenceMarkdown(hourStart, realRows, source, note, hourData, stat, maxCreated, dbHost, fireTs, failureIdentifier);
        } catch (err) {
          console.log(`[throughput-dispatcher] FAIL — createStallIssue failed: ${err.name}: ${err.message}`);
          state.pending_children = state.pending_children || [];
          state.pending_children.push({
            hour_start_iso: hourStart.toISOString(),
            hour_start: hourStart.toISOString(),
            real_rows: realRows,
            source,
            note,
            hour_data: hourData,
            stat,
            max_created: maxCreated,
            db_host: dbHost,
            fire_ts: fireTs,
          });
          console.log(`[throughput-dispatcher] FAIL — buffered child for ${hourStart.toISOString()} (real_rows=${realRows}) in pending_children (${state.pending_children.length} pending total)`);
          failureIdentifier = null;
        }
      } else if (force && realRows < TARGET_ROWS_PER_HOUR) {
        console.log(`[throughput-dispatcher] FAIL (--force override — no issue filed): ${realRows.toLocaleString()} < ${TARGET_ROWS_PER_HOUR.toLocaleString()}`);
      } else if (realRows >= TARGET_ROWS_PER_HOUR) {
        console.log(`[throughput-dispatcher] PASS — ${realRows.toLocaleString()} >= ${TARGET_ROWS_PER_HOUR.toLocaleString()} (source=${source}). No issue filed.`);
        await postParentPassComment(hourStart, realRows, source);
        await writeEvidenceMarkdown(hourStart, realRows, source, note, hourData, stat, maxCreated, dbHost, fireTs);
      } else {
        console.log(`[throughput-dispatcher] BELOW_TARGET — ${realRows.toLocaleString()} < ${TARGET_ROWS_PER_HOUR.toLocaleString()} (source=${source}). No failure child filed: guarded by v6 hard-pass logic.`);
      }
    }

    // Persist state
    if (!dryRun) {
      state.last_n_tup_ins = stat.n_tup_ins;
      state.last_n_tup_ins_at = toPythonIsoString(now);
      state.last_hour_checked = toPythonIsoString(hourStart);
      state.last_check_result = isFirstBaseline
        ? 'BASELINE'
        : source === 'unavailable'
        ? 'ERROR'
        : realRows >= TARGET_ROWS_PER_HOUR
        ? 'PASS'
        : shouldFileFailure
        ? 'FAIL'
        : 'BELOW_TARGET';
      state.last_check_real_rows = realRows;
      state.last_check_source = source;
      state.last_n_live_tup = stat.n_live_tup;
      state.last_db_host = dbHost;
      state.last_hour_window_start = toPythonIsoString(hourStart);
      state.last_hour_window_end = toPythonIsoString(hourEnd);
      state.last_check_threshold = TARGET_ROWS_PER_HOUR;
      state.last_check_delta_rows = deltaInsFromStats;
      state.last_check_rate = realRows;
      state.last_pm_start = pmStart;
      state.last_fire_timestamp = now.toISOString().slice(0, 16) + 'Z';
      state.last_issue_identifier = failureIdentifier;
      if (failureIdentifier) state.last_failure_child_identifier = failureIdentifier;
      state.last_note = buildRunNote({
        hourStart,
        hourEnd,
        result: state.last_check_result,
        realRows,
        source,
        deltaRows: deltaInsFromStats,
        stat,
        pmStart,
        failureIdentifier,
        statResetDetected,
        liveCountDelta,
        nLiveTupDelta,
      });
      saveState(state);
    }
  } finally {
    if (client) client.release();
    await pool.end();
  }

  return 0;
}

if (require.main === module) {
main().then((code) => process.exit(code)).catch((err) => {
  console.error(`[throughput-dispatcher] FATAL: ${err.name}: ${err.message}`);
  if (err.stack) console.error(err.stack);
  process.exit(2);
  });
}

module.exports = {
  isCompletedHour,
  TARGET_ROWS_PER_HOUR,
  selectV6ThroughputSignal,
  shouldFileV6FailureTicket,
  assertV6ForbiddenPatterns,
};
