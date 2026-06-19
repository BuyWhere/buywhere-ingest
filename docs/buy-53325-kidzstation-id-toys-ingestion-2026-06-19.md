# BUY-53325 — Kidz Station Indonesia toys ingestion lane

Date: 2026-06-19
Merchant: Kidz Station Indonesia
URL: https://www.kidzstation.co.id/
Script: `scripts/ingest_kidzstation_id_toys.py`

## Summary

Successfully built and executed the Indonesia toys ingestion lane for Kidz Station Indonesia, a Shopify-based toy retailer carrying LEGO, NERF, Play-Doh, Transformers, and other toy brands.

## Results

| Metric | Value |
|---|---|
| Total API products fetched | 5,599 |
| After dedup | 5,567 |
| Ingested to catalog DB | 5,567 |
| Unique brands | 163 |
| LEGO products | 575 |
| NERF products | 31 |
| Play-Doh products | 60 |
| Transformers products | 57 |

## Brand coverage highlights

The lane covers 163 brands including all major toy families:
- **LEGO** — 575 products (core block, LEGO City, LEGO Friends, etc.)
- **Hasbro brands** — NERF (31), Play-Doh (60), Transformers (57), Monopoly, Hasbro Games/Gaming
- **Other majors** — Barbie, Hot Wheels, Fisher Price, VTech, Disney, Marvel, Pokémon, Gundam, Bandai, Crayola, etc.

## Expected query improvements

This lane directly targets the Toys/Games gap for Indonesia (P2), specifically:
- `lego` — was zeroing due to no dedicated toy merchant in ID source mix
- `lego city`, `nerf`, `transformers toy` — all materially improved with real product coverage

## Ingestion approach

The script uses the Shopify `/collections/all/products.json` API endpoint with 250-item pagination — the fastest method for Shopify stores. No HTML scraping needed.

## Run instructions

```bash
# Full ingestion (fetch + parse + dedup + ingest)
python3 scripts/ingest_kidzstation_id_toys.py

# Snapshot only (no DB ingest)
python3 scripts/ingest_kidzstation_id_toys.py --skip-ingest

# Limited test run
python3 scripts/ingest_kidzstation_id_toys.py --skip-ingest --max-products 100
```

## Data file

Snapshot: `merchants/kidzstation_id_toys_2026-06-19.ndjson` (5,567 products, NDJSON)

## Related issues

- Parent: BUY-53261 — Toys/Games SEA gap-fill
- Child: BUY-53325 — Indonesia toys ingestion lane for Kidz Station Indonesia
