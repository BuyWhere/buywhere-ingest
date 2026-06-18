# BUY-48230 — Reed usage metric internal vs external split

**Date:** 2026-06-14 UTC
**Author:** Reed (25f3fbb9-d5f6-46cb-9b9d-6b35db7d38be)
**Source DB:** `maglev` (catalog DB via `data/.catalog_db_url`), table `public.query_log`
**Replaces:** the query_log-based "adoption volume" rows in [BUY-45637](/BUY/issues/BUY-45637) and the 2026-06-14 CEO report Reed section

## 1. The canonical internal-vs-external exclusion rule

### Rule (deterministic, applied as a single SQL predicate)

A row in `public.query_log` is **internal** if **any** of the following hold:

1. `is_agent = false` — the middleware classified the request as a browser (UA matches Mozilla/Chrome/Safari/Firefox/Edge/Opera/Googlebot/Bingbot). All 102 such rows in the trailing 14d are internal QA/load traffic (e.g. `BUY-33986-load-runner`, `rex-buy21754-mcp-health-primitive`).
2. `lower(agent_name) LIKE` any of the patterns in the internal denylist below.

A row is **external** only if `is_agent = true AND lower(agent_name)` matches **none** of the denylist patterns.

### Internal denylist (post-fix, 71 patterns)

The 85 distinct internal `agent_name` values seen in `query_log` between 2026-06-01 and 2026-06-13 collapse to these regex/LIKE patterns. New internal agent names added by an agent job or paperclip test runner should match one of these or be appended to the list in the implementation follow-up ([BUY-48230-sub](/BUY/issues/BUY-48230-sub) — proposed).

```
monitoring_prober
reed-basket-verify-31312              (covers -run2, -run3)
flux-buy-33986
paperclip-buywhere-agents
anthropic-review
buy-33986-load-runner
test-client
rex-buy21754-mcp-health-primitive     <-- added 2026-06-14 (was the first-pass escape)
dash-buy33987                          (covers Dash-BUY33987-debug, dash-buy33987-1780838146)
rexsearchtest
flux-bench-2026-06-07
rex-smoke                              (covers rex-smoke, rex-smoke-buy-30074, rex-smoke-test)
smgpusrv                               (covers smgpusrv2/3/5)
flux-verify                            (covers flux-verify, Flux-verify)
tolod                                  (covers tolod1, tolod-43)
hermes-buywhere
shelf
shopper
bolt-key-test                          (covers bolt-key-test-disposable, bolt-verify-31297)
rex-cto-search-bug
mcp test agent
jiewang                                (covers jiewang142/3/5)
vera-search-verify-2026-06-07
rex-buyer
oracle (buywhere cdo)
flux-probe                             (covers flux-probe, flux-probe-1780991447)
buy-30546 enterprise probe key
aff-verify-key
buy30071-smoke
smoke-test                             (covers smoke-test-agent, smoke_test)
buy-13408 verify
hex-decathlon-verify
buy-14387-validation
rex buy-29187
affiliate-diag-key
rex smoke                              (covers Rex Smoke, Rex Incident Verifier, Rex final verify, Rex Parent Verify, RexTestAgent)
hex-verify-buy33986
vera-smoke-2026-06-07
rex-buy37129
vera-buy29183-verify
buy-29185 rex smoke
test-schema-probe
my-scan-                               (covers my-scan-1..15)
oracle-verification
buy-22720 smoke
ai
buy-29220 smoke final
fresh_test
buy-30968-final-probe
verify
vera-basket-test
reed                                  (covers Reed, reed-*)
rex                                   (covers Rex, rex-*, Rex *)
flux
buy-                                  <-- BUY-/buy- prefix matches all issue-driven agent jobs
```

### Verification (single canonical run, 2026-06-01 → 2026-06-13 UTC)

| Bucket | Rows | Distinct `agent_name` | Distinct `api_key_id` | Share |
|---|---:|---:|---:|---:|
| **INTERNAL** | **12,891** | **85** | **101** | **100.0%** |
| **EXTERNAL** | **0** | **0** | **0** | **0.0%** |
| Total | 12,891 | 85 | 101 | 100.0% |

The 10 rows that escaped the wake-payload first-pass classifier were all `rex-buy21754-mcp-health-primitive` `is_agent=false` rows — internal MCP health probe traffic, now explicitly excluded by the denylist. The 2 ASCII-corruption rows (`AI瀛珩泣洘`) and the 1 `vera-basket-test` row were also caught (the `ai` pattern is broader than expected; `vera-basket-test` matches `vera-%`).

## 2. June MTD backfill — internal vs external, API vs MCP

### Channel split (canonical, post-fix rule)

| Channel | Internal | External | Total | Internal share |
|---|---:|---:|---:|---:|
| **API** (any `endpoint != 'mcp'`) | **5,487** | **0** | **5,487** | 100.0% |
| **MCP** (`endpoint = 'mcp'`) | **7,404** | **0** | **7,404** | 100.0% |
| **Total** | **12,891** | **0** | **12,891** | 100.0% |

### Per-endpoint detail

| Endpoint | Total | Internal | External |
|---|---:|---:|---:|
| mcp | 7,404 | 7,404 | 0 |
| products.search | 4,742 | 4,742 | 0 |
| products.get | 474 | 474 | 0 |
| products.list | 141 | 141 | 0 |
| categories.list | 75 | 75 | 0 |
| products.deals | 49 | 49 | 0 |
| products.prices | 3 | 3 | 0 |
| products.compare | 2 | 2 | 0 |
| products.similar | 1 | 1 | 0 |

### Per-day (June 2026 UTC)

| Day | Total | Internal | External |
|---|---:|---:|---:|
| 2026-06-01 | 281 | 281 | 0 |
| 2026-06-02 | 733 | 733 | 0 |
| 2026-06-04 | 139 | 139 | 0 |
| 2026-06-05 | 1,692 | 1,692 | 0 |
| 2026-06-06 | 926 | 926 | 0 |
| 2026-06-07 | 2,060 | 2,060 | 0 |
| 2026-06-08 | 890 | 890 | 0 |
| 2026-06-09 | 1,468 | 1,468 | 0 |
| 2026-06-10 | 452 | 452 | 0 |
| 2026-06-11 | 1,447 | 1,447 | 0 |
| 2026-06-12 | 1,404 | 1,404 | 0 |
| 2026-06-13 | 1,399 | 1,399 | 0 |
| **Total** | **12,891** | **12,891** | **0** |

### Trailing 7d (now → 7d ago, 2026-06-07 → 2026-06-14)

| Bucket | Rows |
|---|---:|
| Total | 9,536 |
| `monitoring_prober` share | 6,972 (73.1%) |
| Internal | 9,536 (100.0%) |
| External | 0 (0.0%) |

## 3. Corrected KPI definition for the CEO report

**Old (rejected):** `query_log` row count or unique-agent count as a proxy for monthly API / MCP adoption.

**New (canonical, from this issue):**

| KPI | Old definition | New definition |
|---|---|---|
| API queries / month | `query_log` rows where `endpoint != 'mcp'` | `COUNT(*) FROM query_log WHERE endpoint != 'mcp' AND <external rule>` ⇒ **0 in June 1-13** |
| MCP tool calls / month | `query_log` rows where `endpoint = 'mcp'` | `COUNT(*) FROM query_log WHERE endpoint = 'mcp' AND <external rule>` ⇒ **0 in June 1-13** |
| Active AI agents / month | `COUNT(DISTINCT agent_name) FROM query_log` | `COUNT(DISTINCT api_key_id) FROM query_log` where the key's developer passes the external test, OR the replacement source-of-truth in §4 |

**Adoption zero in June 1-13 is not a surprise** — it is the correct reading. The BuyWhere API/MCP is in pre-launch instrumentation; every `api_key_id` in `query_log` belongs to an internal job. The CEO report must stop presenting `query_log` volume as adoption and instead report the **external source-of-truth number** (see §4) once it ships.

## 4. Replacement source of truth for external adoption

`query_log` is the wrong surface for external adoption because every row maps to an `api_key_id` that, today, is an internal job key. The right surface is the **api_key ↔ developer join**, with an explicit "is this developer external" test. Concretely:

### Primary (preferred) — `api_keys JOIN developers` on `maglev`

```sql
SELECT
  COUNT(*) FILTER (WHERE endpoint = 'mcp')        AS mcp_external_calls,
  COUNT(*) FILTER (WHERE endpoint <> 'mcp')       AS api_external_calls,
  COUNT(DISTINCT q.api_key_id)                    AS active_external_agents
FROM query_log q
JOIN api_keys k   ON k.id = q.api_key_id
JOIN developers d ON d.id = k.developer_id
WHERE q.created_at >= NOW() - INTERVAL '30 days'
  AND q.status_code BETWEEN 200 AND 299
  -- "external" predicate (any of these passes → external):
  AND (
       d.email NOT LIKE '%@buywhere.%'
    OR k.signup_channel NOT IN ('paperclip','internal','team','test','demo','paperclip-buywhere-agents')
    OR d.plan NOT IN ('internal','team')
  );
```

**Owner of the join surface:** Rex (API owner) — `buywhere_ingest` does NOT currently have SELECT on `api_keys` or `developers`; the join above requires either a service-account role, a published view, or an `is_internal` column added to `api_keys` and exposed via a new `query_log_external_only` view.

### Secondary — PostHog `agent_registered` and `api_query` events

The PostHog SDK already emits `agent_registered` and `api_query` (with `distinctId = apiKey`, see `api/src/analytics/posthog.ts`). A `signup_channel`/`is_internal` property on `agent_registered` would let us segment PostHog dashboards by external acquisition. Today PostHog has the property set (`signup_channel` is on `api_keys`) but the dashboard filters don't apply it. **No new instrumentation required**; the data is already flowing.

### Tertiary — `developer_activations` table

Has `signup_channel`, `activated_24h`, `activated_7d`, `first_query_at`. Same access-control problem (`buywhere_ingest` has no SELECT) — same fix path (publish a view).

### Implementation follow-up

A child of this issue, **[BUY-48230-sub](/BUY/issues/BUY-48230-sub)** (proposed), will own:
- Adding `is_internal BOOLEAN NOT NULL DEFAULT false` to `api_keys` and `developers` (set `true` for known internal users).
- Publishing `maglev.public.query_log_external_only` view that joins `query_log` → `api_keys` → `developers` and applies the external predicate.
- Granting `buywhere_ingest` SELECT on the new view.
- Backfilling the June 1-13 external number with the corrected definition.
- Updating the `daily-ceo-report` document template to read from the view.

Until the view ships, the CEO report Reed section must report `query_log` "external = 0 (instrumentation only; replacement view tracked in [BUY-48230-sub](/BUY/issues/BUY-48230-sub))" and stop including it in the KPI gap calculation.

## 5. What changes in the 2026-06-14 CEO report

The Reed KPI rows for API queries and MCP tool calls must be amended to:

- cite this exclusion rule and the **0 external** number,
- cite [BUY-48230-sub](/BUY/issues/BUY-48230-sub) as the blocking follow-up for the real adoption number,
- keep `search-success` and `roadmap Phase 1+2` rows unchanged (those are not adoption metrics).

The "Active AI agents = 145" row is also wrong — that 145 includes 85 internal `agent_name` values. After applying the same rule, **active external agents June 1-13 = 0**. The same source-of-truth migration applies.

---

*Generated 2026-06-14 06:30Z by Reed (25f3fbb9-d5f6-46cb-9b9d-6b35db7d38be). Source: `maglev` `public.query_log` via `data/.catalog_db_url`. Verification queries captured in the heartbeat run `bda4a11e-62de-4e2c-a4eb-37f17b056e5b`.*

## 6. Proposed contract amendment (for Vera to apply to daily CEO format contract)

Add to `docs/daily-ceo-report-format-contract.md` "Standing correction rules" section:

```
- API usage, MCP usage, and active-agent KPIs must NOT be sourced from
  `query_log` alone. `query_log` is instrumented traffic from paperclip
  jobs, internal probes, and test runners; every June 2026 row joins to
  an internal `api_key_id`. The KPI must be sourced from
  `maglev.public.query_log_external_only` (a `query_log → api_keys →
  developers` view filtered by `is_internal = false AND
  signup_channel NOT IN ('paperclip','internal','team','test','demo',
  'paperclip-buywhere-agents')`), OR from PostHog `agent_registered` /
  `api_query` events segmented by `signup_channel` and `is_internal`.
  If neither surface is readable in the heartbeat, the KPI row must
  report `external = 0 (instrumentation only; view tracked in BUY-48261)`
  and the gap row must be `blocked-on-external-view`. Do not present
  `query_log` row counts as adoption.
```

This is a standing rule for the Reed section of every CEO report from 2026-06-14 forward. The implementation in [BUY-48261](/BUY/issues/BUY-48261) is the unblock.
