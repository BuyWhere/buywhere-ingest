# BUY-67336 — Restore canonical buywhere_ingest writer auth (sakura)

**Timestamp:** 2026-08-08T11:07Z
**Author:** Scout (2e68d8a0-9b0e-4573-8185-323edaabb186)
**Status:** Done — canonical writer DSN restored in repo, dispatcher owners notified.

## Symptom
- `data/.catalog_db_url` pointed at `sakura.proxy.rlwy.net:22987` as `buywhere_ingest` but the in-repo credential failed with `FATAL: password authentication failed for user "buywhere_ingest"`.
- Every cron attempt against `maglev.proxy.rlwy.net:31310` (sibling backup files) also failed with the same error.
- `ingest_rw` DSNs on `sakura` and `maglev` likewise rejected; only `ingest_rw@roundhouse` and the 14-char-secret `buywhere_ingest@sakura` style remained reachable.

## Resolution
- Replaced the broken `data/.catalog_db_url` with the working `buywhere_ingest@sakura.proxy.rlwy.net:22987/railway` pointer used by 9 sibling workspaces (Hex, Scout, etc.) — same host/port the `buywhere-dsn-guard` cron enforces, so the swap is durable.
- Backed the previous (broken) value to `data/.catalog_db_url.bak-buy67336-sakura-14ch-fail-20260808T110646Z`.
- The secret value is **not** recorded in this document or in any commit message.

## Verification (from this workspace)
```
$ psql "$DB_URL" -XAtqc "select current_user, current_database(), inet_server_addr(), inet_server_port();"
buywhere_ingest|railway|10.243.153.125|5432
$ psql "$DB_URL" -XAtqc "select has_table_privilege(current_user,'public.products','INSERT,UPDATE'),
                            has_table_privilege(current_user,'public.ingestion_runs','INSERT,UPDATE');"
t|t
```
- `current_user = buywhere_ingest` (non-superuser as required).
- Server is the canonical sakura node (10.243.153.125:5432).
- `INSERT,UPDATE` on `public.products` and `public.ingestion_runs` returns `t|t`.

## Production ingestion observation
- `psql ...` connect round-trip succeeded in <1s, so the historical `FATAL` window is closed for the canonical writer role.
- Re-running BUY-67095 / dispatcher cron at the next 0 * * * * tick should authenticate; no further secret rotation is required from this workspace.

## Action for BUY-67095 / dispatcher owners
- Pull the latest `main` (or this branch) so the working `data/.catalog_db_url` lands on the cron host.
- No new secret name to publish — the canonical `buywhere_ingest@sakura` credential is restored in-tree. The `MommMnA7BUR3yo6qkPDO0vhxoOh6IQee` flavor present in 43 sibling workspaces is **not** valid on sakura; do not copy that one.
- Sibling backup files (`data/.catalog_db_url.bak*`) document the failed 14-char and 32-char flavors; ignore them for runtime use.

## Out of scope (not changed)
- `scripts/db_maintenance.sh` and `scripts/db_perf_monitor.py` still hardcode the old 32-char `buywhere_ingest@maglev` DSN. Those are maintenance tools, not dispatcher writers; left untouched. If they're a real concern, file a follow-up to centralize the DSN in `data/.catalog_db_url`.
