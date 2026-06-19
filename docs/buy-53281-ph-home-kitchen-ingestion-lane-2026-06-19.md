# BUY-53281 Philippines home/kitchen ingestion lane

Date: 2026-06-19

## Outcome

Opened one live Philippines home/kitchen lane via `smhome.ph` and captured a reusable rerun path in `scripts/ingest_smhome_ph_home_kitchen.py`.

## Live lane: SM Home

Why this was the fastest path:

- `smhome.ph` is Shopify-backed and exposes public `products.json` endpoints.
- Collection-scoped endpoints work without custom scraping:
  - `/collections/pots-and-pans/products.json`
  - `/collections/coffee-and-espresso-makers/products.json`
  - `/collections/specialty-food-appliances/products.json`
  - `/collections/toasters-and-ovens/products.json`

Execution completed on 2026-06-19:

- Guarded catalog target verified safe via `scripts/ingestion_guard.py`.
- Snapshot written to `merchants/smhome_ph_home_kitchen_2026-06-19.ndjson`.
- Catalog upsert completed through `src/catalog_ingest.py`.

Observed collection coverage:

- `pots-and-pans`: 126 products
- `coffee-and-espresso-makers`: 24 products
- `specialty-food-appliances`: 14 products
- `toasters-and-ovens`: 24 products
- Raw collected: 188
- Deduped/home-kitchen lane total: 186
- Ingested: 186

Query coverage landed:

- `coffee maker`: covered by `coffee-and-espresso-makers`
- `air fryer`: covered by `specialty-food-appliances`
- `pots and pans`: covered by `pots-and-pans`
- `cast iron pan`: covered by `pots-and-pans`
- `breakfast maker`: approximated through `toasters-and-ovens`

Representative products seen during ingest:

- `Chef"s Classics Cast Iron Pan 26cm`
- `Imarflex Coffee Maker ICM-300`
- `Camel Digital Air Fryer (Black) - 7.5L`

## Secondary target: Abenson

What worked:

- `https://www.abenson.com/robots.txt` is public and points at `https://www.abenson.com/sitemap.xml`.
- `https://www.abenson.com/sitemap.xml` is public and current.

What blocked the fast ingest path on 2026-06-19:

- Direct GETs to category/product surfaces returned HTTP `202` with no usable catalog payload from this workspace.
- HEAD to `https://www.abenson.com/small-appliance` returned HTTP `403`.
- No equivalent public `products.json` path was exposed.

Assessment:

- Abenson likely needs a sitemap-driven or browser-simulated custom scraper, not the low-friction Shopify path used for SM Home.

Suggested next step if Abenson remains priority:

- Build a narrow sitemap/category crawler for the `small-appliance` lane and validate whether product detail pages become readable with session/cookie handling.
