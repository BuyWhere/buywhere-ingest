# Daily 3.5M Product Source-Mix Plan

Date: 2026-06-05 UTC
Issue: BUY-29843
Parent: BUY-29843
Owner: Oracle

## Target Window

- Fixed planning target for this report: `3,500,000` products/day
- Planning window: `2026-06-05` through `2026-06-30` (`26` calendar days inclusive)
- Gross plan volume if hit every day: `91,000,000`
- Current active-product gap to `100,000,000` from the latest canonical shortfall snapshot (`2026-06-04`): `83,204,398`
- Gross overage versus the current active-product gap if the full `3.5M/day` plan actually lands every day: `7,795,602`

## Evidence Used

1. [docs/daily-product-target-shortfall-2026-06-04.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-04.md)
   - canonical active products: `16,795,602`
   - fully closed `2026-06-03` UTC day movement: `0` creates, `0` updates, `0` active-product growth
2. [BUY-29210](/BUY/issues/BUY-29210)
   - last merchant-attributed canonical write evidence on `2026-06-02` UTC: `paper_source = 10`, `floor_and_decor = 3`, `the_body_shop = 5`
3. [docs/buy-29215-shopper-merchant-acquisition-lane-2026-06-02.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-29215-shopper-merchant-acquisition-lane-2026-06-02.md)
   - acquisition lane remains a small, manually-supported scrape lane, not yet configured as a mass-ingest route
4. [docs/daily-source-mix-plan-2026-06-04.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-source-mix-plan-2026-06-04.md)
   - carries forward all lane commitments and blockers from the last completed run
5. Repo execution inventory remains unchanged at this heartbeat (from previous run):
   - [data/.merchant_configs.json](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/data/.merchant_configs.json) still names only `paper_source`, `floor_and_decor`, and `the_body_shop`
   - [scripts/catalog_live_ingest.py](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/scripts/catalog_live_ingest.py) still hardcodes only those three plus `courts_sg`
   - [src/scrapers/__init__.py](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/src/scrapers/__init__.py) still registers `29` scraper classes; none are yet integrated into sustained daily canonical volume commitments

## Daily Source-Mix Plan

| Source family | Merchant lane | Owner | Expected products for `2026-06-05` plan | Checkpoint-backed | Planned-only | Dependency / blocker | Status |
|---|---|---|---:|---:|---:|---|---|
| Live scrape -> canonical maglev | `paper_source` | Shopper acquisition lane (`BUY-29215`) + Oracle | 10 | 10 | 0 | sustained-write recovery under [BUY-29835](/BUY/issues/BUY-29835) | historically proven once, not proven sustained |
| Live scrape -> canonical maglev | `floor_and_decor` | Shopper acquisition lane (`BUY-29215`) + Oracle | 3 | 3 | 0 | sustained-write recovery under [BUY-29835](/BUY/issues/BUY-29835) | historically proven once, not proven sustained |
| Live scrape -> canonical maglev | `the_body_shop` | Shopper acquisition lane (`BUY-29215`) + Oracle | 0 | 5 | 0 | repeated `429` responses observed on last run (`2026-06-04`); blocked until rate-limit recovery |
| Uncovered remainder | no merchant-assigned lane | Oracle / Rex / Shopper | 3,499,987 | 0 | 3,499,987 | [BUY-29835](/BUY/issues/BUY-29835) plus missing large-batch merchant packages beyond the current three-lane set | no executable source mix exists yet |
| Total | all lanes | Oracle | 3,500,000 | 18 | 3,499,987 |  | plan is `0.0005%` checkpoint-backed |

## What This Means

- There is still no credible `2026-06-05` source mix that can account for the full `3,500,000` products/day target from currently checkpoint-backed lanes.
- Merchant-attributed evidence remains effectively capped at `18` rows (from `2026-06-02` recovery artifacts), and there is still no sustained canonical write movement visible in fully closed days.
- Plan risk is unchanged vs `2026-06-04`: `3,499,987 / 3,500,000` products remain planned-only or fully unassigned with this lane set.
- The largest active risk remains the stalled sustained-write path under [BUY-29835](/BUY/issues/BUY-29835), not a template or reporting-gap issue.

## Ownership Map

- Oracle owns the daily scoreboard, exact gap callout, and checkpoint-evidence discipline on this report path.
- Shopper's lane in [BUY-29215](/BUY/issues/BUY-29215) owns sourcing merchant packages and expected volumes for potential next lanes.
- The sustained-write path and recovery continuity are owned by [BUY-29835](/BUY/issues/BUY-29835); until that path shows fresh canonical DB movement, this report remains largely checkpoint-unbacked.

## Next Reporting Rule

For each future daily run, carry forward the same table shape and only increase a lane's committed `Expected products` count when all of the following are true:

1. a merchant lane has a named owner
2. the lane has exact expected daily volume
3. the lane has fresh checkpoint evidence on the canonical pinned DB
4. the lane is not currently blocked by site-rate limits or a catalog-write freeze
