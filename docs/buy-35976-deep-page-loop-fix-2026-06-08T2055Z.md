# BUY-35976 — deep-page loop death diagnosis and containment (2026-06-08T20:55Z)

## Root cause

The repeated `deep_page_loop` deaths were caused by the lane doing oversized
work batches, then disappearing before it could finish a cycle and persist
state. The pre-fix log shows the same `cursor=640, cycle=5748` starting over on
each keep-alive restart while attempting 80-domain batches that produced
59k-79k products in a single cycle. There is no handled `FATAL:` or
`cycle error:` line for those deaths, which points to abrupt termination under
mid-cycle pressure rather than an application-level exception path.

## Fix

The live Oracle workspace script
`/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/scripts/buy30590-deep-page-loop.mjs`
was contained by reducing the default deep-page work shape:

- `DEEP_PAGE_BATCH_DOMAINS` lowered to `8`
- `DEEP_PAGE_CONCURRENCY` lowered to `4`
- both settings are env-tunable for future retuning

## Verification

Post-fix lane behavior changed immediately:

- `2026-06-08T20:49:31.947Z` restarted at `cursor=640, cycle=5748`
- `2026-06-08T20:50:30.743Z` completed `deep cycle 5749: 8 domains -> 1 hit -> 13336 deep products`
- `2026-06-08T20:51:27.462Z` completed `deep cycle 5750 ingest: exit=0 3.9s`
- `2026-06-08T20:51:41.162Z` completed `deep cycle 5752 ingest: exit=0 2.3s`
- `2026-06-08T20:53:46.369Z` advanced into `deep cycle 5753`

State and keep-alive proof after the containment:

- `data/buy30590-deep-page-state.json` advanced to `{"cursor":680,"cycle":5753}`
- `data/buy30854-keep-alive-state.json` reset `deep_page_loop` to `0`
- manual keep-alive tick at `2026-06-08T20:53:51Z` reported `deep_page_loop OK pid=2662992`
- spot check at `2026-06-08T20:54:59Z` showed the same PID still alive at `elapsed=05:27`

## Conclusion

The smallest durable fix for this incident was to reduce the lane's default
batch pressure. The lane is now surviving past the prior failure window, making
forward progress, and no longer triggering the keep-alive dead counter.
