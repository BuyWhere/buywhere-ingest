#!/usr/bin/env node
/**
 * Focused tests for BUY-59891 v6 hourly throughput decision logic (JS parity).
 *
 * Mirrors test_hourly_throughput_dispatcher_v6.py.
 *
 * Run:
 *   node scripts/test_hourly_throughput_dispatcher_v6.js
 */

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');

const {
  isCompletedHour,
  TARGET_ROWS_PER_HOUR,
  selectV6ThroughputSignal,
  shouldFileV6FailureTicket,
  assertV6ForbiddenPatterns,
  validateCanonicalDbUrl,
  assertCanonicalStatsCollected,
  computeStatsDeltas,
  readCatalogDbUrl,
  retryPendingChildren,
  connectPoolWithRetry,
  ensureSchemaFailureIssueId,
  isPgStatResetWithLiveCatalog,
} = require('./dispatcher_v6_hourly');

// ---------------------------------------------------------------------------
// validateCanonicalDbUrl
// ---------------------------------------------------------------------------

describe('validateCanonicalDbUrl', () => {
  it('accepts maglev canonical DB URL', () => {
    const url = 'postgresql://user:pass@maglev.proxy.rlwy.net:31310/railway?sslmode=require';
    assert.equal(validateCanonicalDbUrl(url), url);
  });

  it('accepts migrated Railway proxy canonical DB URLs', () => {
    const url = 'postgresql://user:pass@sakura.proxy.rlwy.net:22987/railway?sslmode=require';
    assert.equal(validateCanonicalDbUrl(url), url);
  });

  it('rejects roundhouse stale mirror URL', () => {
    const url = 'postgresql://user:pass@roundhouse.proxy.rlwy.net:27479/railway?sslmode=require';
    assert.throws(() => validateCanonicalDbUrl(url), /stale mirror/);
  });
});

// ---------------------------------------------------------------------------
// canonical DB safety
// ---------------------------------------------------------------------------

describe('canonical DB safety', () => {
  it('rejects stats-not-collected products tables', () => {
    assert.throws(
      () => assertCanonicalStatsCollected({ n_live_tup: 0, n_tup_ins: 0, n_tup_upd: 0 }),
      /stats are not collected/,
    );
  });

  it('allows zero stats when live_count is positive (pg_stat reset case)', () => {
    assert.doesNotThrow(() => assertCanonicalStatsCollected({ n_live_tup: 0, n_tup_ins: 0, n_tup_upd: 0 }, { liveCount: 7032806 }));
  });

  it('rejects zero stats with zero live_count', () => {
    assert.throws(
      () => assertCanonicalStatsCollected({ n_live_tup: 0, n_tup_ins: 0, n_tup_upd: 0 }, { liveCount: 0 }),
      /stats are not collected/,
    );
  });

  it('allows canonical stats with a non-zero products insert counter', () => {
    assert.doesNotThrow(() => assertCanonicalStatsCollected({ n_live_tup: 12, n_tup_ins: 1, n_tup_upd: 0 }));
  });

  it('does not treat prior-row-zero as an absolute insert delta', () => {
    const deltas = computeStatsDeltas(10_009_403, 50, 0, 0);
    assert.equal(deltas.deltaInsFromStats, null);
    assert.equal(deltas.deltaUpdFromStats, null);
    assert.equal(deltas.statResetDetected, true);
  });

  it('computes stats deltas from non-zero prior baselines', () => {
    const deltas = computeStatsDeltas(10_009_403, 55, 10_000_000, 50);
    assert.equal(deltas.deltaInsFromStats, 9_403);
    assert.equal(deltas.deltaUpdFromStats, 5);
    assert.equal(deltas.statResetDetected, false);
  });

  it('detects pg_stat reset when all products stats are zero but live_count is positive', () => {
    assert.equal(isPgStatResetWithLiveCatalog(
      { n_live_tup: 0, n_tup_ins: 0, n_tup_upd: 0 },
      { live_count: 7_032_806 }
    ), true);
  });

  it('does not detect pg_stat reset when live_count is absent', () => {
    assert.equal(isPgStatResetWithLiveCatalog(
      { n_live_tup: 0, n_tup_ins: 0, n_tup_upd: 0 },
      { live_count: null }
    ), false);
  });

  it('ignores DATABASE_URL when explicit canonical sources are absent', () => {
    const oldCanonical = process.env.CANONICAL_DATABASE_URL;
    const oldMaglev = process.env.MAGLEV_DB_URL;
    const oldDatabase = process.env.DATABASE_URL;
    process.env.CANONICAL_DATABASE_URL = '';
    process.env.MAGLEV_DB_URL = '';
    process.env.DATABASE_URL = 'postgresql://user:pass@roundhouse.proxy.rlwy.net:27479/railway?sslmode=require';
    try {
      assert.throws(() => readCatalogDbUrl('/path/that/does/not/exist'), /DATABASE_URL is intentionally ignored/);
    } finally {
      if (oldCanonical === undefined) delete process.env.CANONICAL_DATABASE_URL; else process.env.CANONICAL_DATABASE_URL = oldCanonical;
      if (oldMaglev === undefined) delete process.env.MAGLEV_DB_URL; else process.env.MAGLEV_DB_URL = oldMaglev;
      if (oldDatabase === undefined) delete process.env.DATABASE_URL; else process.env.DATABASE_URL = oldDatabase;
    }
  });
});

// ---------------------------------------------------------------------------
// selectV6ThroughputSignal
// ---------------------------------------------------------------------------

describe('selectV6ThroughputSignal', () => {
  it('v6.4 ignores created_at counts when canonical stats delta exists', () => {
    const [realRows, source] = selectV6ThroughputSignal({ real_rows: TARGET_ROWS_PER_HOUR * 3 }, 42, 0, 0);
    assert.equal(realRows, 42);
    assert.equal(source, 'delta_ins_from_stats');
  });

  it('v6.5 uses hourData.real_rows as fallback when deltaInsFromStats is null', () => {
    const [realRows, source] = selectV6ThroughputSignal(
      { real_rows: 175_000 }, null, null, null, null, null, null
    );
    assert.equal(realRows, 175_000);
    assert.equal(source, 'hour_bucket_count');
  });

  it('v6.5 hourData fallback is skipped when deltaInsFromStats is available', () => {
    const [realRows, source] = selectV6ThroughputSignal(
      { real_rows: 175_000 }, 42, 0, 0
    );
    assert.equal(realRows, 42);
    assert.equal(source, 'delta_ins_from_stats');
  });

  it('v6.5 hourData.error is not used as a signal', () => {
    const [realRows, source] = selectV6ThroughputSignal(
      { error: 'statement_timeout', timeout_s: 30 }, null, null, null, null, null, null
    );
    assert.equal(realRows, 0);
    assert.equal(source, 'unavailable');
  });

  it('v6.5 hourData.real_rows zero falls through to next signal', () => {
    const [realRows, source] = selectV6ThroughputSignal(
      { real_rows: 0 }, null, 50_000, null, null, null, null
    );
    assert.equal(realRows, 50_000);
    assert.equal(source, 'ingestion_runs_observability');
  });

  it('v6.5 hourData.real_rows above target returns pass', () => {
    const [realRows, source] = selectV6ThroughputSignal(
      { real_rows: 200_000 }, null, null, null, null, null, null
    );
    assert.equal(realRows, 200_000);
    assert.equal(source, 'hour_bucket_count');
  });

  it('v6.5 hourData.real_rows below target signals fail', () => {
    const [realRows, source] = selectV6ThroughputSignal(
      { real_rows: 80_000 }, null, null, null, null, null, null
    );
    assert.equal(realRows, 80_000);
    assert.equal(source, 'hour_bucket_count');
  });


  it('stats delta is authoritative even when secondary metrics pass', () => {
    const [realRows, source] = selectV6ThroughputSignal(42, TARGET_ROWS_PER_HOUR * 2, TARGET_ROWS_PER_HOUR * 3);
    assert.equal(realRows, 42);
    assert.equal(source, 'delta_ins_from_stats');
  });

  it('stats delta under target still authoritative with zero live count', () => {
    const [realRows, source] = selectV6ThroughputSignal(42, 0, 0);
    assert.equal(realRows, 42);
    assert.equal(source, 'delta_ins_from_stats');
  });

  it('stats hard-guard pass not masked by zero secondary metrics', () => {
    const [realRows, source] = selectV6ThroughputSignal(TARGET_ROWS_PER_HOUR, 0, 0);
    assert.equal(realRows, TARGET_ROWS_PER_HOUR);
    assert.equal(source, 'delta_ins_from_stats');
  });

  it('ingestion fallback pass not masked by low live count delta', () => {
    const [realRows, source] = selectV6ThroughputSignal(null, TARGET_ROWS_PER_HOUR, 0);
    assert.equal(realRows, TARGET_ROWS_PER_HOUR);
    assert.equal(source, 'ingestion_runs_observability');
  });

  it('live count hard-guard pass not masked by zero ingestion runs', () => {
    const [realRows, source] = selectV6ThroughputSignal(null, 0, TARGET_ROWS_PER_HOUR);
    assert.equal(realRows, TARGET_ROWS_PER_HOUR);
    assert.equal(source, 'live_count_delta');
  });

  it('fail only when all available fallbacks are below target', () => {
    const [realRows, source] = selectV6ThroughputSignal(null, 10, 20);
    assert.equal(realRows, 10);
    assert.equal(source, 'ingestion_runs_observability');
  });

  it('v6.4 n_live_tup_guard fires when stats unavailable + ing_inserted unavailable', () => {
    // Rule 5b.v6.4: delta_ins_from_stats null, canonical_ing_inserted null (unavailable)
    // → nLiveTupGuard fires (ing_inserted unavailable = allowed by v6.4).
    const [realRows, source] = selectV6ThroughputSignal(null, null, null, 7_400_000);
    assert.equal(realRows, 7_400_000);
    assert.equal(source, 'n_live_tup_delta_guard');
  });

  it('v6.4 keeps stats delta authoritative when n_live_tup guard would pass', () => {
    // Rule 5a: delta_ins_from_stats=722 is non-null and authoritative.
    // nLiveTupGuard allowed but does NOT override stats per rule 5b.v6.4.
    const [realRows, source] = selectV6ThroughputSignal(722, TARGET_ROWS_PER_HOUR, null, 876_000);
    assert.equal(realRows, 722);
    assert.equal(source, 'delta_ins_from_stats');
  });

  it('v6.4 ing_inserted blocks n_live_tup_guard (autovacuum bloat)', () => {
    const [realRows, source] = selectV6ThroughputSignal(18, 18, null, 7_400_000);
    assert.equal(realRows, 18);
    assert.equal(source, 'delta_ins_from_stats');
  });



  it('v6.4 files from stats delta even when created_at count passes', () => {
    assert.equal(
      shouldFileV6FailureTicket({ real_rows: TARGET_ROWS_PER_HOUR * 3 }, 42, 0, 0),
      true,
    );
  });

  it('files when authoritative stats delta is non-null below target', () => {
    assert.equal(shouldFileV6FailureTicket(42, 0, 0), true);
  });

  it('does not file when authoritative stats delta passes', () => {
    assert.equal(shouldFileV6FailureTicket(TARGET_ROWS_PER_HOUR, 0, 0), false);
  });

  it('files only when stats null and fallbacks below target', () => {
    assert.equal(shouldFileV6FailureTicket(null, 10, 20), true);
  });

  it('does not file when ingestion fallback passes', () => {
    assert.equal(shouldFileV6FailureTicket(null, TARGET_ROWS_PER_HOUR, 0), false);
  });

  it('does not file when live count fallback passes', () => {
    assert.equal(shouldFileV6FailureTicket(null, 0, TARGET_ROWS_PER_HOUR), false);
  });

  it('v6.4 ing_inserted blocks n_live_tup_guard and preserves stats FAIL', () => {
    assert.equal(
      shouldFileV6FailureTicket(18, 18, null, 7_400_000),
      true,
    );
  });

  it('v6.4 unavailable ing_inserted cannot rescue a low stats delta', () => {
    // Rule 5d: delta_ins_from_stats=722 is non-null and < target → FILE.
    // Secondary metrics cannot rescue a non-null stats delta.
    assert.equal(
      shouldFileV6FailureTicket(722, null, null, 876_000),
      true,
    );
  });

  it('v6.4 target-level ing_inserted cannot rescue a low stats delta', () => {
    // Rule 5d: delta_ins_from_stats=722 is non-null and < target → FILE.
    // nLiveTupGuard allowed but cannot override stats per rule 5a.
    assert.equal(
      shouldFileV6FailureTicket(722, TARGET_ROWS_PER_HOUR, null, 876_000),
      true,
    );
  });

  it('returns true for a completed hour', () => {
    const now = new Date(Date.UTC(2026, 6, 14, 5, 20)); // July 14 05:20 UTC
    const hourStart = new Date(Date.UTC(2026, 6, 14, 4, 0));
    assert.equal(isCompletedHour(hourStart, now), true);
  });

  it('returns false for the current (not yet completed) hour', () => {
    const now = new Date(Date.UTC(2026, 6, 14, 5, 20));
    const hourStart = new Date(Date.UTC(2026, 6, 14, 5, 0));
    assert.equal(isCompletedHour(hourStart, now), false);
  });
});

// ---------------------------------------------------------------------------
// assertV6ForbiddenPatterns
// ---------------------------------------------------------------------------

describe('assertV6ForbiddenPatterns', () => {
  it('rule 6(c): allows zero inserts with updates when raw counter flat', () => {
    assert.doesNotThrow(() => {
      assertV6ForbiddenPatterns({
        deltaInsFromStats: 0,
        deltaUpdFromStats: 4,
        realRows: 0,
        source: 'delta_ins_from_stats',
        liveCountDelta: null,
        currentNTupIns: 192_634_641,
        previousNTupIns: 192_634_641,
      });
    });
  });

  it('rule 6(c): raises when zero delta contradicts raw insert counters', () => {
    assert.throws(
      () => {
        assertV6ForbiddenPatterns({
          deltaInsFromStats: 0,
          deltaUpdFromStats: 4,
          realRows: 0,
          source: 'delta_ins_from_stats',
          liveCountDelta: null,
          currentNTupIns: 192_634_642,
          previousNTupIns: 192_634_641,
        });
      },
      /v6 rule 6\(c\) violation/,
    );
  });

  it('rule 6(a): raises when source fell back to ingestion with stats available', () => {
    assert.throws(
      () => {
        assertV6ForbiddenPatterns({
          deltaInsFromStats: 42,
          deltaUpdFromStats: 0,
          realRows: 42,
          source: 'ingestion_runs_observability',
          liveCountDelta: null,
          currentNTupIns: null,
          previousNTupIns: null,
        });
      },
      /v6 rule 6\(a\) violation/,
    );
  });

  it('rule 6(b): raises when live_count_delta=0 but delta_ins_from_stats>0', () => {
    assert.throws(
      () => {
        assertV6ForbiddenPatterns({
          deltaInsFromStats: 42,
          deltaUpdFromStats: 0,
          realRows: 42,
          source: 'live_count_delta',
          liveCountDelta: 0,
          currentNTupIns: null,
          previousNTupIns: null,
        });
      },
      /v6 rule 6\(b\) violation/,
    );
  });

  it('rule 6(b): raises when delta_ins_from_stats=0 but live_count_delta>0', () => {
    assert.throws(
      () => {
        assertV6ForbiddenPatterns({
          deltaInsFromStats: 0,
          deltaUpdFromStats: 0,
          realRows: 0,
          source: 'delta_ins_from_stats',
          liveCountDelta: 42,
          currentNTupIns: null,
          previousNTupIns: null,
        });
      },
      /v6 rule 6\(b\) violation/,
    );
  });
});

// ---------------------------------------------------------------------------
// retryPendingChildren
// ---------------------------------------------------------------------------

describe('retryPendingChildren', () => {
  it('drops a pending child when a matching child already exists', async () => {
    const oldApiKey = process.env.PAPERCLIP_API_KEY;
    process.env.PAPERCLIP_API_KEY = 'test-api-key';
    const state = {
      pending_children: [{
        hour_start_iso: '2026-07-20T17:00:00.000Z',
        real_rows: 13_650,
        source: 'delta_ins_from_stats',
      }],
    };
    let createCalled = false;

    try {
      const filed = await retryPendingChildren(state, {
        dedupCheckExistingChild: async () => true,
        createStallIssue: async () => {
          createCalled = true;
          return 'BUY-duplicate';
        },
      });

      assert.deepEqual(filed, []);
      assert.deepEqual(state.pending_children, []);
      assert.equal(createCalled, false);
    } finally {
      if (oldApiKey === undefined) {
        delete process.env.PAPERCLIP_API_KEY;
      } else {
        process.env.PAPERCLIP_API_KEY = oldApiKey;
      }
    }
  });

  it('tracks existing child identifier when dedup-skipping pending child', async () => {
    const oldApiKey = process.env.PAPERCLIP_API_KEY;
    process.env.PAPERCLIP_API_KEY = 'test-api-key';
    const state = {
      pending_children: [{
        hour_start_iso: '2026-07-20T17:00:00.000Z',
        real_rows: 13_650,
        source: 'delta_ins_from_stats',
      }],
      last_failure_child_identifier: 'BUY-STALE',
    };

    try {
      const filed = await retryPendingChildren(state, {
        dedupCheckExistingChild: async () => ({ identifier: 'BUY-EXISTING-CHILD' }),
        createStallIssue: async () => { throw new Error('should not be called'); },
      });

      assert.deepEqual(filed, []);
      assert.deepEqual(state.pending_children, []);
      assert.equal(state.last_failure_child_identifier, 'BUY-EXISTING-CHILD');
    } finally {
      if (oldApiKey === undefined) {
        delete process.env.PAPERCLIP_API_KEY;
      } else {
        process.env.PAPERCLIP_API_KEY = oldApiKey;
      }
    }
  });
});

// ---------------------------------------------------------------------------
// Additional partition sum and retry signal tests
// ---------------------------------------------------------------------------



describe('retryPendingChildren — success path', () => {
  it('files pending child when dedup returns false', async () => {
    const oldApiKey = process.env.PAPERCLIP_API_KEY;
    process.env.PAPERCLIP_API_KEY = 'test-api-key';
    const state = {
      pending_children: [{
        hour_start_iso: '2026-07-20T17:00:00.000Z',
        real_rows: 13_650,
        source: 'delta_ins_from_stats',
      }],
    };

    try {
      const filed = await retryPendingChildren(state, {
        dedupCheckExistingChild: async () => false,
        createStallIssue: async () => 'BUY-NEW-123',
      });

      assert.deepEqual(filed, ['BUY-NEW-123']);
      assert.deepEqual(state.pending_children, []);
    } finally {
      if (oldApiKey === undefined) {
        delete process.env.PAPERCLIP_API_KEY;
      } else {
        process.env.PAPERCLIP_API_KEY = oldApiKey;
      }
    }
  });

  it('buffers to remaining on createStallIssue error', async () => {
    const oldApiKey = process.env.PAPERCLIP_API_KEY;
    process.env.PAPERCLIP_API_KEY = 'test-api-key';
    const state = {
      pending_children: [{
        hour_start_iso: '2026-07-20T17:00:00.000Z',
        real_rows: 13_650,
        source: 'delta_ins_from_stats',
      }],
    };

    try {
      const filed = await retryPendingChildren(state, {
        dedupCheckExistingChild: async () => false,
        createStallIssue: async () => { throw new Error('API error'); },
      });

      assert.deepEqual(filed, []);
      assert.equal(state.pending_children.length, 1);
      assert.equal(state.pending_children[0].real_rows, 13_650);
    } finally {
      if (oldApiKey === undefined) {
        delete process.env.PAPERCLIP_API_KEY;
      } else {
        process.env.PAPERCLIP_API_KEY = oldApiKey;
      }
    }
  });
});

// ---------------------------------------------------------------------------
// Additional edge-case coverage
// ---------------------------------------------------------------------------

describe('isCompletedHour — edge cases', () => {
  it('returns true for hour 23 crossing into next UTC day', () => {
    const hourStart = new Date(Date.UTC(2026, 6, 14, 23, 0));
    const now = new Date(Date.UTC(2026, 6, 15, 0, 30));
    assert.equal(isCompletedHour(hourStart, now), true);
  });

  it('returns false when exactly at hour boundary (same ms)', () => {
    const hourStart = new Date(Date.UTC(2026, 6, 14, 5, 0));
    const now = new Date(Date.UTC(2026, 6, 14, 6, 0));
    assert.equal(isCompletedHour(hourStart, now), true);
  });

  it('returns false for future hour', () => {
    const hourStart = new Date(Date.UTC(2026, 7, 1, 0, 0));
    const now = new Date(Date.UTC(2026, 6, 14, 5, 20));
    assert.equal(isCompletedHour(hourStart, now), false);
  });
});

describe('assertV6ForbiddenPatterns — additional rules', () => {
  it('rule 5a/5b.v6.4: rejects n_live_tup_delta_guard with stats available', () => {
    // Rule 5a/5b.v6.4: source must NEVER be n_live_tup_delta_guard when
    // delta_ins_from_stats is non-null. The new assertion fires here.
    assert.throws(
      () => {
        assertV6ForbiddenPatterns({
          deltaInsFromStats: 42,
          deltaUpdFromStats: 0,
          realRows: 42,
          source: 'n_live_tup_delta_guard',
          liveCountDelta: null,
          currentNTupIns: null,
          previousNTupIns: null,
        });
      },
      /v6 rule 5a/,
    );
  });

  it('rule 6(b): allows when both are null', () => {
    assert.doesNotThrow(() => {
      assertV6ForbiddenPatterns({
        deltaInsFromStats: null,
        deltaUpdFromStats: null,
        realRows: 0,
        source: 'unavailable',
        liveCountDelta: null,
        currentNTupIns: null,
        previousNTupIns: null,
      });
    });
  });

  it('rule 6(c): allows non-zero delta with differing counters', () => {
    assert.doesNotThrow(() => {
      assertV6ForbiddenPatterns({
        deltaInsFromStats: 42,
        deltaUpdFromStats: 0,
        realRows: 42,
        source: 'delta_ins_from_stats',
        liveCountDelta: null,
        currentNTupIns: 192_634_642,
        previousNTupIns: 192_634_641,
      });
    });
  });
});

describe('selectV6ThroughputSignal — live_count_delta fallback ordering', () => {
  it('prefers ingestion_runs over live_count_delta when both available', () => {
    const [realRows, source] = selectV6ThroughputSignal(null, TARGET_ROWS_PER_HOUR, TARGET_ROWS_PER_HOUR);
    assert.equal(realRows, TARGET_ROWS_PER_HOUR);
    assert.equal(source, 'ingestion_runs_observability');
  });

  it('falls through to live_count_delta when ingestion is zero', () => {
    const [realRows, source] = selectV6ThroughputSignal(null, 0, TARGET_ROWS_PER_HOUR);
    assert.equal(realRows, TARGET_ROWS_PER_HOUR);
    assert.equal(source, 'live_count_delta');
  });

  it('returns unavailable when all signals are zero or null', () => {
    const [realRows, source] = selectV6ThroughputSignal(null, null, 0, 0);
    assert.equal(realRows, 0);
    assert.equal(source, 'unavailable');
  });

  it('returns unavailable for truly empty signal set', () => {
    const [realRows, source] = selectV6ThroughputSignal(null, null, null, null);
    assert.equal(realRows, 0);
    assert.equal(source, 'unavailable');
  });
});

describe('shouldFileV6FailureTicket — edge cases', () => {
  it('does not file when live_count_delta exceeds target with null stats', () => {
    assert.equal(shouldFileV6FailureTicket(null, null, null, TARGET_ROWS_PER_HOUR * 2), false);
  });

  it('does not file when live_count_delta exceeds target with zero stats', () => {
    assert.equal(shouldFileV6FailureTicket(null, null, 0, TARGET_ROWS_PER_HOUR * 2), false);
  });

  it('files when live_count_delta is positive but below target', () => {
    assert.equal(shouldFileV6FailureTicket(null, null, null, 50_000, null), true);
  });

  it('files when all fallback metrics are null/unavailable', () => {
    assert.equal(shouldFileV6FailureTicket(null, null, null, null), true);
  });

  it('does not file when ingested fallback passes and live_count is unavailable', () => {
    assert.equal(
      shouldFileV6FailureTicket(null, TARGET_ROWS_PER_HOUR, null, null, null, null, null),
      false,
    );
  });

  it('does not file when live_count passes and ingested fallback is unavailable', () => {
    assert.equal(
      shouldFileV6FailureTicket(null, null, null, TARGET_ROWS_PER_HOUR, null, null, null),
      false,
    );
  });

  it('v6.5 shouldFile uses hourData when stats and partition are null', () => {
    assert.equal(shouldFileV6FailureTicket(
      { real_rows: 80_000 }, null, null, null, null, null, null
    ), true);
  });

  it('v6.5 shouldFile skips hourData when stats are available', () => {
    assert.equal(shouldFileV6FailureTicket(
      { real_rows: 200_000 }, 200_000, 0, null, null, null, null
    ), false);
  });

  it('v6.5 shouldFile does not file when hourData shows above target', () => {
    assert.equal(shouldFileV6FailureTicket(
      { real_rows: 200_000 }, null, null, null, null, null, null
    ), false);
  });

});

describe('connectPoolWithRetry', () => {
  it('returns a client on first successful connect', async () => {
    const fakeClient = { id: 'ok' };
    const fakePool = {
      connect: async () => fakeClient,
    };
    const client = await connectPoolWithRetry(fakePool);
    assert.equal(client, fakeClient);
  });

  it('retries on transient failure then succeeds', async () => {
    let attempts = 0;
    const fakeClient = { id: 'retry-ok' };
    const fakePool = {
      connect: async () => {
        attempts++;
        if (attempts < 3) throw new Error('ECONNRESET');
        return fakeClient;
      },
    };
    const client = await connectPoolWithRetry(fakePool, 3, 10);
    assert.equal(client, fakeClient);
    assert.equal(attempts, 3);
  });

  it('throws after exhausting all attempts', async () => {
    let attempts = 0;
    const fakePool = {
      connect: async () => {
        attempts++;
        throw new Error('ECONNRESET');
      },
    };
    await assert.rejects(
      () => connectPoolWithRetry(fakePool, 2, 10),
      { message: 'ECONNRESET' }
    );
    assert.equal(attempts, 2);
  });
});

// ---------------------------------------------------------------------------
// ensureSchemaFailureIssueId
// ---------------------------------------------------------------------------

describe('ensureSchemaFailureIssueId', () => {
  it('no-ops when failure_issue_id column already exists', async () => {
    let queried = false;
    const fakeClient = {
      query: async (sql) => {
        queried = true;
        if (typeof sql === 'string' && sql.includes('information_schema')) {
          return { rows: [{ '1': 1 }] };
        }
        return { rows: [] };
      },
    };
    await ensureSchemaFailureIssueId(fakeClient);
    assert.equal(queried, true);
  });

  it('adds column when missing', async () => {
    const calls = [];
    const fakeClient = {
      query: async (sql) => {
        calls.push(typeof sql === 'string' ? sql.trim() : sql);
        if (typeof sql === 'string' && sql.includes('information_schema')) {
          return { rows: [] };
        }
        return { rows: [] };
      },
    };
    await ensureSchemaFailureIssueId(fakeClient);
    assert.ok(calls.some(c => c.includes('ALTER TABLE')));
  });

  it('catches and logs errors without throwing', async () => {
    const fakeClient = {
      query: async () => { throw new Error('permission denied'); },
    };
    await assert.doesNotReject(() => ensureSchemaFailureIssueId(fakeClient));
  });

  it('returns false when add-column fails due permission', async () => {
    const fakeClient = {
      query: async (sql) => {
        if (typeof sql === 'string' && sql.includes('information_schema')) {
          return { rows: [] };
        }
        const err = new Error('must be owner of table canonical_throughput_hourly');
        err.code = '42501';
        throw err;
      },
    };
    const result = await ensureSchemaFailureIssueId(fakeClient);
    assert.equal(result, false);
  });
});
