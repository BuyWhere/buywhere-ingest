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
  retryPendingChildren,
  connectPoolWithRetry,
} = require('./dispatcher_v6_hourly');

// ---------------------------------------------------------------------------
// selectV6ThroughputSignal
// ---------------------------------------------------------------------------

describe('selectV6ThroughputSignal', () => {
  it('v6.4 ignores created_at counts when canonical stats delta exists', () => {
    const [realRows, source] = selectV6ThroughputSignal({ real_rows: TARGET_ROWS_PER_HOUR * 3 }, 42, 0, 0);
    assert.equal(realRows, 42);
    assert.equal(source, 'delta_ins_from_stats');
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

  it('v6.4 n_live_tup_guard fires when stats below + ing_inserted unavailable', () => {
    const nLiveTup = 7_400_000;
    const [realRows, source] = selectV6ThroughputSignal(722, null, null, nLiveTup);
    assert.equal(realRows, nLiveTup);
    assert.equal(source, 'n_live_tup_delta_guard');
  });

  it('v6.4 n_live_tup_guard fires when stats below + ing_inserted corroborates target', () => {
    const nLiveTup = 876_000;
    const [realRows, source] = selectV6ThroughputSignal(722, TARGET_ROWS_PER_HOUR, null, nLiveTup);
    assert.equal(realRows, nLiveTup);
    assert.equal(source, 'n_live_tup_delta_guard');
  });

	  it('v6.4 ing_inserted blocks n_live_tup_guard (autovacuum bloat)', () => {
	    const [realRows, source] = selectV6ThroughputSignal(18, 18, null, 7_400_000);
	    assert.equal(realRows, 18);
	    assert.equal(source, 'delta_ins_from_stats');
	  });

	  it('v6.4 stats delta stays authoritative when partition sum is stale', () => {
	    const [realRows, source] = selectV6ThroughputSignal(
	      { real_rows: 0 },
	      TARGET_ROWS_PER_HOUR + 6_028,
	      0,
	      null,
	      151_426,
	      0,
	      0,
	    );
	    assert.equal(realRows, TARGET_ROWS_PER_HOUR + 6_028);
	    assert.equal(source, 'delta_ins_from_stats');
	  });

  it('ignores zero partition sentinel when no authoritative stats delta exists', () => {
    const [realRows, source] = selectV6ThroughputSignal(
      { real_rows: 0 },
      null,
      null,
      null,
      null,
      0,
      0,
    );
    assert.equal(realRows, 0);
    assert.equal(source, 'unavailable');
    assert.equal(
      shouldFileV6FailureTicket({ real_rows: 0 }, null, null, null, null, 0, 0),
      false,
    );
  });
	});

// ---------------------------------------------------------------------------
// shouldFileV6FailureTicket
// ---------------------------------------------------------------------------

describe('shouldFileV6FailureTicket', () => {
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

  it('v6.4 unavailable ing_inserted preserves stale-counter guard (PASS)', () => {
    assert.equal(
      shouldFileV6FailureTicket(722, null, null, 876_000),
      false,
    );
  });

	  it('v6.4 target-level ing_inserted preserves stale-counter guard (PASS)', () => {
	    assert.equal(
	      shouldFileV6FailureTicket(722, TARGET_ROWS_PER_HOUR, null, 876_000),
	      false,
	    );
	  });

	  it('v6.4 does not file when stats delta passes despite stale partition sum', () => {
	    assert.equal(
	      shouldFileV6FailureTicket(
	        { real_rows: 0 },
	        TARGET_ROWS_PER_HOUR + 6_028,
	        0,
	        null,
	        151_426,
	        0,
	        0,
	      ),
	      false,
	    );
	  });
	});

// ---------------------------------------------------------------------------
// isCompletedHour
// ---------------------------------------------------------------------------

describe('isCompletedHour', () => {
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

describe('selectV6ThroughputSignal — partition sum fallback', () => {
  it('uses partition sum when stats delta is null', () => {
    // current=200K, previous=50K → delta=150K
    const [realRows, source] = selectV6ThroughputSignal(null, null, null, null, null, 200_000, 50_000);
    assert.equal(realRows, 150_000);
    assert.equal(source, 'partition_sum_n_tup_ins');
  });

  it('partition sum below target still fails', () => {
    const [realRows, source] = selectV6ThroughputSignal(null, null, null, null, null, 100_000, 0);
    assert.equal(realRows, 100_000);
    assert.equal(source, 'partition_sum_n_tup_ins');
  });

  it('stats delta takes precedence over partition sum', () => {
    // deltaIns=42 (non-null) should be chosen even if partition sum is available
    const [realRows, source] = selectV6ThroughputSignal(null, 42, null, null, null, 200_000, 50_000);
    assert.equal(realRows, 42);
    assert.equal(source, 'delta_ins_from_stats');
  });
});

describe('shouldFileV6FailureTicket — partition sum path', () => {
  it('files when partition sum below target and no stats delta', () => {
    assert.equal(shouldFileV6FailureTicket(null, null, null, null, null, 100_000, 50_000), true);
  });

  it('does not file when partition sum passes target', () => {
    assert.equal(shouldFileV6FailureTicket(null, null, null, null, null, 200_000, 0), false);
  });
});

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
  it('rule 6(a): allows when source is n_live_tup_delta_guard with stats available', () => {
    assert.doesNotThrow(() => {
      assertV6ForbiddenPatterns({
        deltaInsFromStats: 42,
        deltaUpdFromStats: 0,
        realRows: 42,
        source: 'n_live_tup_delta_guard',
        liveCountDelta: null,
        currentNTupIns: null,
        previousNTupIns: null,
      });
    });
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
