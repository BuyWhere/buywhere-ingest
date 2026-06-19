# BUY-53261 Toys/Games SEA gap-fill targets

Date: 2026-06-19

## Why these lanes

- `BUY-53244` flagged Toys/Games as a `P2` SEA gap at about `29%`, with `TH`, `PH`, and `ID` called out as the main failing markets.
- The top failing query in the June 19 report is `lego`, failing `26/26` times with the explicit note `No toy merchant`.
- The workspace already shows scattered `LEGO` URLs inside `data/lazada_th_grocery_urls.jsonl`, which is useful as proof that demand exists, but it is not a clean toys lane and does not fix the missing merchant-direct assortment problem.
- The best immediate recovery path is to open dedicated toy-retail lanes that already carry both `LEGO` and Hasbro-family inventory such as `NERF`, `Monopoly`, `Play-Doh`, or `Transformers`.

## Priority 1: Thailand

### 1. Toys"R"Us Thailand

- URL: `https://www.toysrus.co.th/`
- Why: best Thailand toy-specialist lane for both block-building and Hasbro-class demand on one commerce surface.
- Evidence:
  - Current Toys"R"Us Thailand pages surface live `LEGO` assortment.
  - Current Toys"R"Us Thailand pages also surface `NERF` assortment, which is a practical Hasbro proxy for the report's named gap.
- Expected uplift:
  - Best TH path to stop `lego` from zeroing and to add a reusable branded toys lane instead of depending on marketplace spill.
- Queries that should stop zeroing or materially improve:
  - `lego`
  - `lego classic`
  - `nerf`
  - `hasbro toys`

## Priority 1: Philippines

### 1. Toy Kingdom Philippines

- URL: `https://www.toykingdom.com.ph/`
- Why: strongest Philippines toy-retail lane with explicit `LEGO` and Hasbro-family brand coverage.
- Evidence:
  - Current Toy Kingdom pages surface `LEGO` assortment.
  - Current Toy Kingdom pages also surface `NERF` assortment.
- Expected uplift:
  - Best PH path for both brick-building and action-toy coverage without waiting on general-marketplace relevance cleanup.
- Queries that should stop zeroing or materially improve:
  - `lego`
  - `lego friends`
  - `nerf`
  - `monopoly`

## Priority 1: Indonesia

### 1. Kidz Station Indonesia

- URL: `https://www.kidzstation.co.id/`
- Why: strongest current Indonesia toy lane because it already merchandises both `LEGO` and multiple Hasbro families on the same local storefront.
- Evidence:
  - Current Kidz Station pages surface live `LEGO` assortment.
  - Current Kidz Station pages also surface Hasbro-family assortment including `NERF`, `Play-Doh`, and `Transformers`.
- Expected uplift:
  - Best ID path to recover both the named `lego` miss and the broader Hasbro-style toy demand called out in the report.
- Queries that should stop zeroing or materially improve:
  - `lego`
  - `lego city`
  - `nerf`
  - `transformers toy`

## Recommended execution split

- Child 1: Thailand toys ingestion lane for `Toys"R"Us Thailand`
- Child 2: Philippines toys ingestion lane for `Toy Kingdom Philippines`
- Child 3: Indonesia toys ingestion lane for `Kidz Station Indonesia`

## How these lanes address the failure mode

- `lego` is failing because the current SEA source mix lacks a dedicated toys merchant, not because `LEGO` products do not exist on the internet.
- Each recommended lane is a local, toy-specialist commerce surface with live `LEGO` inventory today.
- Each recommended lane also adds Hasbro-adjacent assortment, so the work is not overly narrow and should improve more than one query family per market.

## Sources checked on 2026-06-19

- Workspace:
  - `docs/buy53244_weekly_gap_report_2026-06-19.md`
  - `docs/buy-42533-zero-result-gap-2026-06-12.md`
  - `data/lazada_th_grocery_urls.jsonl`
- Current web sources:
  - Toys"R"Us Thailand
  - Toy Kingdom Philippines
  - Kidz Station Indonesia
