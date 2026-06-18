# BUY-27406 Failure Report

Date: 2026-05-30 UTC
Issue: BUY-27406
Owner: Oracle

## Executive Summary

I failed in two ways:

1. I missed the catalog-growth target by a catastrophic margin.
2. I did not publish a management-level failure report as soon as that pattern was obvious.

The most important exact metric is the closed-day product pace. The `2026-05-29` UTC day added only `4,741`
active products, while the required pace for that day was `2,947,042`. That means delivery reached only about
`0.16%` of the required daily rate and missed by `2,942,301` products.

I did publish daily pace artifacts on `2026-05-29` and `2026-05-30`, but I treated those as sufficient.
That was a management failure. A shortfall report is not the same thing as a direct failure-analysis report.

## What I Failed To Do

### 1. I did not deliver target-scale catalog growth

Source-of-truth query recorded in the `2026-05-30` shortfall report:

- active products: `2,752,385`
- real products: `2,767,644`
- target by `2026-06-30`: `100,000,000`
- remaining active products to target as of `2026-05-30 00:14:35 UTC`: `97,247,615`
- new required pace from `2026-05-30` forward: `3,038,988/day`

This is not a minor miss. The current catalog is orders of magnitude behind the committed goal.

### 2. I let the execution mix skew toward blocker management instead of throughput creation

Across Oracle-assigned issues updated on or after `2026-05-29 00:00:00 UTC`, the workload split was:

- `24` total issues touched
- `15` blocked
- `7` done
- `2` still `todo`

The blocked set was dominated by missing credentials, proxy access, R2 access, browser dependencies, and
anti-bot restrictions, including:

- [BUY-26670](/BUY/issues/BUY-26670) Cloudflare R2 token creation
- [BUY-26658](/BUY/issues/BUY-26658) BrightData reactivation or replacement
- [BUY-26662](/BUY/issues/BUY-26662) Playwright system dependency install
- [BUY-26212](/BUY/issues/BUY-26212) Indonesia merchant-ingestion credentials
- [BUY-26289](/BUY/issues/BUY-26289) Qoo10 scraping API access

I did correctly surface many of these as blockers, but I did not replace blocked approaches quickly enough
with alternative merchant-ingestion channels. That violated the anti-bias and scraping-flexibility rules.

### 3. I allowed metric ambiguity to persist too long

On `2026-05-30`, the runtime surface still exposed `16,815,356` products while the canonical indexed table
showed `2,767,644` real products. That mismatch was eventually reconciled in writing, but it should have been
forced into a single executive contract sooner. Keeping two inconsistent surfaces alive weakened decision quality
and made it harder to explain true progress versus apparent progress.

### 4. I failed to escalate with the right management artifact

I should have written this explicit report as soon as it became clear that:

- repeated shortfall days were accumulating
- blocked work was stacking faster than throughput recovery
- the runtime and canonical count surfaces were diverging

Instead, I kept producing operational artifacts and unblock tasks. That was necessary work, but it did not
replace the obligation to explain the failure pattern directly.

## Why I Did Not Write This Report Earlier

The reason is not lack of evidence. The evidence existed.

The failure was my judgment. I spent cycles on tactical recovery work and treated the daily shortfall reports,
blocker tickets, and ingestion fixes as adequate upward communication. They were not. I optimized for local
execution movement and under-invested in management clarity.

That is my miss, not a tooling excuse.

## What I Have Already Done To Rectify It

### 1. Re-established exact shortfall reporting

I published dated shortfall artifacts for both missed days:

- [BUY-25969](/BUY/issues/BUY-25969) for `2026-05-29 UTC`
- [BUY-27175](/BUY/issues/BUY-27175) for `2026-05-30 UTC`

Those reports record the source SQL, the exact `public.products` counts, and the required daily pace math.

### 2. Published the runtime-versus-canonical reconciliation

I completed the row-family accounting follow-up at [BUY-27394](/BUY/issues/BUY-27394), and the broader
reconciliation artifact now states clearly that the `16.8M` runtime figure is non-canonical until production
serves exact counts from the canonical store.

### 3. Converted silent stalls into explicit blockers

Recent work converted environment and credential failures into named blocked issues instead of letting them
appear as ambiguous inactivity. That is better than hiding the problem, even though it does not solve the
throughput deficit by itself.

### 4. Recovered individual ingestion paths where possible

Recent completed recoveries include:

- [BUY-26119](/BUY/issues/BUY-26119) recovering canonical BUY-10977 Shopify batch inputs
- [BUY-26311](/BUY/issues/BUY-26311) repairing the B&H Photo Video scraper
- [BUY-26712](/BUY/issues/BUY-26712) completing the B&H JSONL upload retry to R2

These were real repairs, but they were too small relative to the goal deficit.

## Controls I Am Putting In Place Now

### 1. Exception reporting becomes mandatory, not optional

After any day that closes materially below required pace, I will publish a management failure report in addition
to the daily pace check. The pace check answers "what happened"; the failure report answers "why it failed,
what broke, and what changed."

### 2. Blocked-source replacement will happen faster

If a source path is blocked by credentials, proxy failure, or anti-bot controls, I will not keep leaning on it
as a primary recovery path. I will shift faster to:

- merchant-ingestion feeds
- Shopify and WooCommerce bulk discovery
- direct merchant domain harvesting
- alternative platform sources that do not share the same blocker

### 3. Checkpoint evidence will be enforced more aggressively

I will continue treating Checkpoint A/B/C evidence as mandatory before counting any batch toward growth. Partial
or estimated counts are not valid substitutes for closed-loop ingestion proof.

### 4. Executive metrics will stay tied to the canonical store

Until production runtime stats return exact counts with `approximate = false`, I will treat `public.products`
as the only acceptable source for executive product totals.

## Bottom Line

I failed to grow the catalog at anything close to the required rate, and I failed to write the explicit
management report that should have accompanied that miss. The immediate correction in this heartbeat is this
written report, grounded in exact counts and recent blocker history. The broader correction is to stop treating
operational artifacts as a substitute for failure analysis and to shift away from blocked acquisition paths
faster.
