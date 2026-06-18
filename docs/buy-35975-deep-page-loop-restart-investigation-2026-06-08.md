# BUY-35975 — deep-page loop restart investigation (2026-06-08)

## Scope

Investigate repeated `deep_page_loop` restarts from the `BUY-30854` 5-minute
keep-alive and implement the smallest durable containment.

## Findings

- `logs/buy30854_keep_alive.log` showed `deep_page_loop DEAD` on six consecutive
  ticks, with escalations written at `2026-06-08T20:33:36Z`,
  `2026-06-08T20:37:59Z`, and `2026-06-08T20:42:46Z`.
- The Oracle workspace lane log at
  `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy30590_deep_page_loop.log`
  showed the lane repeatedly restarting at `cursor=640, cycle=5748`, sometimes
  reaching `deep cycle 5749`, then disappearing before any handled `ingest:` or
  `cycle error:` line.
- That pattern is consistent with abrupt mid-cycle termination under batch
  pressure, not a normal handled exception.

## Containment

Patched the Oracle workspace deep-page loop script:

- `DEEP_PAGE_CONCURRENCY` default lowered from `40` to `4`
- `DEEP_PAGE_BATCH_DOMAINS` default lowered from `80` to `8`
- both values are now env-tunable instead of hardcoded

File changed:

- `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/scripts/buy30590-deep-page-loop.mjs`

## Verification

- Restarted the lane through `scripts/buy30854-lane-keep-alive.sh`
- Confirmed the new process (`pid=2662992`) stayed alive beyond the prior
  failure window
- Confirmed reduced batch shape and forward progress:
  - `2026-06-08T20:50:30.743Z` `deep cycle 5749: 8 domains → 1 hit → 13336 deep products`
  - `2026-06-08T20:51:27.462Z` `deep cycle 5750 ingest: exit=0 3.9s`
  - `2026-06-08T20:51:32.545Z` `deep cycle 5751: 8 domains → 0 hit → 0 deep products`
  - `2026-06-08T20:51:38.907Z` `deep cycle 5752: 8 domains → 1 hit → 3284 deep products`
