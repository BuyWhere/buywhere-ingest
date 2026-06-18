# Daily 3.5M Product Source-Mix Plan

Date: 2026-06-04 UTC
Issue: BUY-29847
Parent: BUY-29843
Owner: Oracle

## Target Window

- Fixed planning target for this report: `3,500,000` products/day
- Planning window: `2026-06-04` through `2026-06-30` (`27` calendar days inclusive)
- Gross plan volume if hit every day: `94,500,000`
- Current active-product gap to `100,000,000` from the canonical catalog at the `2026-06-04` shortfall snapshot: `83,204,398`
- Gross overage versus the current active-product gap if the full `3.5M/day` plan actually lands every day: `11,295,602`

## Evidence Used

1. [docs/daily-product-target-shortfall-2026-06-04.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-04.md)
   - canonical active products: `16,795,602`
   - fully closed `2026-06-03` UTC day movement: `0` creates, `0` updates, `0` active-product growth
2. [BUY-29210](/BUY/issues/BUY-29210)
   - last merchant-attributed canonical write evidence on `2026-06-02` UTC: `paper_source = 10`, `floor_and_decor = 3`, `the_body_shop = 5`
3. [docs/buy-29215-shopper-merchant-acquisition-lane-2026-06-02.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-29215-shopper-merchant-acquisition-lane-2026-06-02.md)
   - current merchant-acquisition path is still a small configured live-scrape lane, not a mass-ingest lane
4. `python3 scripts/catalog_live_ingest.py --all --limit 10 --dry-run` on `2026-06-04`
   - ingestion guard passed against the canonical pinned DB
   - the run did not complete into a fresh success package before this report cutoff
   - `the_body_shop` returned repeated `429 Too Many Requests`, so that lane is not currently reliable enough to count toward today's committed mix
5. Repo execution inventory at this heartbeat
   - [data/.merchant_configs.json](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/data/.merchant_configs.json)
     still names only `paper_source`, `floor_and_decor`, and `the_body_shop`
   - [scripts/catalog_live_ingest.py](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/scripts/catalog_live_ingest.py)
     still hardcodes only those three plus `courts_sg`
   - [src/scrapers/__init__.py](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/src/scrapers/__init__.py)
     registers `29` scraper classes total, but the additional inventory is not
     yet wired into this live writer path with named daily volume commitments

## Daily Source-Mix Plan

| Source family | Merchant lane | Owner | Expected products for `2026-06-04` plan | Checkpoint-backed | Planned-only | Dependency / blocker | Status |
|---|---|---|---:|---:|---:|---|---|
| Live scrape -> canonical maglev | `paper_source` | Shopper acquisition lane (`BUY-29215`) + Oracle | 10 | 10 | 0 | sustained-write recovery under [BUY-29835](/BUY/issues/BUY-29835) | historically proven once, not proven sustained |
| Live scrape -> canonical maglev | `floor_and_decor` | Shopper acquisition lane (`BUY-29215`) + Oracle | 3 | 3 | 0 | sustained-write recovery under [BUY-29835](/BUY/issues/BUY-29835) | historically proven once, not proven sustained |
| Live scrape -> canonical maglev | `the_body_shop` | Shopper acquisition lane (`BUY-29215`) + Oracle | 0 | 5 | 0 | fresh site rate-limit failures on `2026-06-04`; sustained-write recovery under [BUY-29835](/BUY/issues/BUY-29835) | blocked today by `429` responses |
| Uncovered remainder | no merchant-assigned lane | Oracle / Rex / Shopper | 3,499,987 | 0 | 3,499,987 | [BUY-29835](/BUY/issues/BUY-29835) plus missing large-batch merchant packages beyond the current three-lane set | no executable source mix exists yet |
| Total | all lanes | Oracle | 3,500,000 | 18 | 3,499,987 |  | plan is `0.0005%` checkpoint-backed |

## What This Means

- There is no credible `2026-06-04` source mix that explains how `3,500,000` products will be produced today from the currently evidenced merchant lanes.
- The only merchant-attributed canonical evidence I can defend in this runner is `18` rows total from the `2026-06-02` recovery package, and even that package did not continue into the fully closed `2026-06-03` UTC day.
- The current exact gap in the plan is not a reporting nuance. It is a real execution gap:
  - only `18 / 3,500,000` planned products are checkpoint-backed
  - `3,499,987 / 3,500,000` remain planned-only or fully unassigned
  - one of the three currently configured merchant lanes is actively rate-limited today
- The broader repo scraper inventory does not close that gap by itself. Until
  those sources are wired into the canonical live-ingest path with named owners
  and exact expected volumes, they do not count as committed source mix.

## Ownership Map

- Oracle owns the daily scoreboard, exact gap callout, and checkpoint-evidence discipline on this report path.
- Shopper's lane in [BUY-29215](/BUY/issues/BUY-29215) owns sourcing the next merchant packages with expected volumes large enough to matter.
- The sustained-write failure itself is owned in [BUY-29835](/BUY/issues/BUY-29835); until that issue shows fresh canonical DB movement after `2026-06-03`, this report should continue treating almost the entire `3.5M/day` plan as uncovered.

## Next Reporting Rule

For each future daily run on this lane, carry forward the same table shape and only increase a lane's committed `Expected products` count when all of the following are true:

1. a merchant lane has a named owner
2. the lane has exact expected daily volume
3. the lane has fresh checkpoint evidence on the canonical pinned DB
4. the lane is not currently blocked by site-rate limits or a catalog-write freeze
