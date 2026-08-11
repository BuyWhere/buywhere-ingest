import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { finalizeDiscoverRun } from '../src/ingestionRunStatus.js';

describe('finalizeDiscoverRun', () => {
  it('fails all-dead discover runs with a first-class error message', () => {
    assert.deepEqual(finalizeDiscoverRun(0, 0, 120), {
      status: 'failed',
      errorMessage: 'all_probes_dead:120',
    });
  });

  it('uses completed_with_errors when inserts coexist with dead probes', () => {
    assert.deepEqual(finalizeDiscoverRun(1, 0, 3), {
      status: 'completed_with_errors',
      errorMessage: null,
    });
    assert.deepEqual(finalizeDiscoverRun(0, 2, 3), {
      status: 'completed_with_errors',
      errorMessage: null,
    });
  });

  it('keeps clean discover runs completed', () => {
    assert.deepEqual(finalizeDiscoverRun(4, 1, 0), {
      status: 'completed',
      errorMessage: null,
    });
  });
});