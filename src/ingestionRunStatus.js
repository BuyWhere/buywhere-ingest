export function finalizeDiscoverRun(insertedNew, insertedExisting, rowsFailed) {
  const inserted = Number(insertedNew || 0) + Number(insertedExisting || 0);
  const failed = Number(rowsFailed || 0);

  if (failed > 0 && inserted === 0) {
    return { status: 'failed', errorMessage: `all_probes_dead:${failed}` };
  }

  if (failed > 0) {
    return { status: 'completed_with_errors', errorMessage: null };
  }

  return { status: 'completed', errorMessage: null };
}