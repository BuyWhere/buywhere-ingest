# BUY-53259 Sports/Activewear SEA gap-fill targets

Date: 2026-06-19

## Why this lane

- `BUY-53244` flagged Sports/Activewear as a P1 SEA gap and specifically called out `Nike`, `Adidas`, and `Lululemon` as absent in the June 19 report.
- The workspace shows that "absent across SEA" is too strong for Singapore: `merchants/zalora_sg_2026-06-06.ndjson` already contains live `Nike` and `ADIDAS` products, including:
  - `Nike` — `Miler Dri-FIT 12.5cm (approx.) Brief-Lined Running Shorts`
  - `ADIDAS` — `Adizero Evo SL Shoes`
  - `ADIDAS` — `3-Stripes Crew Socks 3 Pairs`
- The stronger diagnosis is:
  - SG has at least partial marketplace coverage through `zalora_sg`.
  - The dedicated `nike_sg` lane is currently broken or stale for current capture needs: `data/nike_sg_scheduler.jsonl` logged `product_count: 0` on `2026-06-12T05:52:15.960637+00:00`.
  - Direct-brand coverage is still thin or absent in the SEA countries that matter most for query recovery outside SG.

## Priority 1: Thailand

### 1. Nike Thailand

- URL: `https://www.nike.com/th/`
- Why: cleanest direct-brand fix for one of the most frequently named misses in the weekly report.
- Evidence:
  - Nike Thailand currently exposes a full local storefront with shoes, clothing, accessories, and sport-specific entry points including football, running, basketball, gym/training, and tennis.
  - The live `/th/w` product surface is indexed now, confirming online sellable assortment rather than store-locator-only presence.
- Expected uplift:
  - Strong recovery for branded Nike footwear/apparel queries in TH.
  - Better match quality for sport-intent searches like `running shoes`, `football boots`, and team-jersey queries.

### 2. adidas Thailand

- URL: `https://www.adidas.co.th/en`
- Why: direct-brand counterpart to Nike TH with broad footwear, apparel, and sportswear depth.
- Evidence:
  - adidas Thailand currently markets shoes, clothing, activewear, and sportswear on the official Thailand site.
  - Current category pages for men's and women's sportswear are live, which is useful for both product and category extraction.
- Expected uplift:
  - Strong recovery for `Adidas` branded search plus general activewear/running/football queries in TH.
  - Lower brand-normalization ambiguity than third-party marketplace-only sourcing.

### 3. Supersports Thailand

- URL: `https://www.supersports.co.th/en`
- Why: broad Thailand sports retailer with both Nike and Adidas already merchandised online; best non-brand fallback if direct lanes are slow to land.
- Evidence:
  - Supersports Thailand currently exposes dedicated `Nike` and `Adidas` collection pages.
  - The live site structure also exposes running and football apparel trees, which aligns with the report's zero-result symptoms.
- Expected uplift:
  - Directional estimate: `+10K to +25K` TH sports/apparel SKUs after overlap and dedup.
  - Broadens branded and category recovery beyond what a single direct brand lane will provide.

## Priority 1: Indonesia

### 1. Nike Indonesia

- URL: `https://www.nike.com/id/`
- Why: direct local Nike lane for one of the report's named brand misses in a thin SEA market.
- Evidence:
  - Nike Indonesia currently exposes a local commerce site with live product listing pages under `/id/w`.
  - The product surface includes football boots, shirts, shoes, and accessories in current indexing.
- Expected uplift:
  - Immediate recovery path for `Nike` branded queries in ID.
  - Better coverage for performance-running and football-led search demand.

### 2. adidas Indonesia

- URL: `https://www.adidas.co.id/en`
- Why: official Indonesia catalog with clear shoes/clothing/sportswear depth.
- Evidence:
  - adidas Indonesia currently markets shoes, clothing, Originals, running, football, and training on the official site.
  - Live category pages are already indexed with concrete products and prices.
- Expected uplift:
  - Immediate recovery path for `Adidas` brand and sport-category queries in ID.
  - More reliable activewear normalization than relying on marketplace snippets alone.

### 3. PlanetSports.Asia Indonesia

- URL: `https://www.planetsports.asia/`
- Why: high-value multi-brand Indonesia sports retailer that already carries both `Nike` and `Adidas`.
- Evidence:
  - PlanetSports.Asia currently exposes brand navigation for `Adidas` and `Nike`.
  - The live Adidas collection page is indexed with shoes and apparel assortment in Indonesia.
- Expected uplift:
  - Directional estimate: `+8K to +20K` ID sports/apparel SKUs after overlap and dedup.
  - Good fallback if direct-brand anti-bot or catalog-shape issues slow Nike/adidas first-party ingestion.

## Priority 2: Malaysia

### 1. Nike Malaysia

- URL: `https://www.nike.com/my/`
- Why: official Nike local storefront with category depth already visible.
- Evidence:
  - Nike Malaysia currently exposes shoes, clothing, accessories/equipment, and shop-by-sport navigation.
  - Men's and sale/product pages are live now, confirming current online assortment.

### 2. adidas Malaysia

- URL: `https://www.adidas.com.my/en`
- Why: official adidas local storefront with broad footwear, apparel, and sportswear categories.
- Evidence:
  - adidas Malaysia currently markets classic and new shoes, clothing, activewear, and sportswear, plus women's category depth and store presence.

### 3. lululemon Malaysia

- URL: `https://www.lululemon.com.hk/en-my/home`
- Why: clean direct route for the report's third named miss, especially yoga/athleisure and women's activewear queries.
- Evidence:
  - lululemon Malaysia currently serves a dedicated `en-my` storefront with local-market routing.
  - The brand's Southeast Asia presence is materially visible online now, which makes Malaysia a workable landing point even if PH/VN/ID need marketplace or regional follow-ons.

## Priority 3: Singapore / cross-SEA marketplace fallback

### 1. ZALORA Singapore

- URL: `https://www.zalora.sg/`
- Why: already proven in-workspace to contain `Nike` and `ADIDAS`; immediate correction target for the report narrative and a possible brand-normalization cleanup lane.
- Evidence:
  - Local artifact `merchants/zalora_sg_2026-06-06.ndjson` contains live `Nike` and `ADIDAS` product URLs.
  - Web indexing also shows current ZALORA SG Nike category pages.
- Expected uplift:
  - Not a new-market unlock, but a fast path to improve SG brand recall and correct false "absence" assumptions.

### 2. ZALORA Indonesia

- URL: `https://www.zalora.co.id/s/sports`
- Why: multi-brand sports marketplace with explicit `Nike` and `Adidas` merchandising already visible.
- Evidence:
  - ZALORA Indonesia currently markets sportswear from `Nike`, `Adidas`, `Puma`, and `Under Armour`.
  - Current Nike and Adidas product pages are live and indexed now.

### 3. ZALORA Malaysia / Philippines

- URLs:
  - `https://www.zalora.com.my/`
  - `https://www.zalora.com.ph/`
- Why: useful fallback if direct-brand onboarding for MY or PH hits anti-bot/commercial friction first.
- Evidence:
  - ZALORA Malaysia currently exposes live Nike and Adidas product pages.
  - ZALORA Philippines currently exposes a large fashion/sports catalog and an indexed Adidas collection.

## Recommended execution split

- Child 1: Thailand direct-brand ingestion for `Nike TH` + `adidas TH`
- Child 2: Indonesia direct-brand ingestion for `Nike ID` + `adidas ID`
- Child 3: Thailand/Indonesia marketplace fallback for `Supersports TH` + `PlanetSports.Asia`
- Child 4: Brand-normalization and SG correction pass for `zalora_sg` plus follow-on `Nike SG` scraper repair if direct SG coverage is still needed
- Child 5: Malaysia activewear follow-up for `Nike MY` + `adidas MY` + `lululemon MY`

## Sources checked on 2026-06-19

- Workspace:
  - `merchants/zalora_sg_2026-06-06.ndjson`
  - `data/nike_sg_scheduler.jsonl`
- Current web sources:
  - Nike Thailand: `https://www.nike.com/th/`
  - adidas Thailand: `https://www.adidas.co.th/en`
  - Supersports Thailand: `https://www.supersports.co.th/en`
  - Nike Indonesia: `https://www.nike.com/id/`
  - adidas Indonesia: `https://www.adidas.co.id/en`
  - PlanetSports.Asia: `https://www.planetsports.asia/`
  - Nike Malaysia: `https://www.nike.com/my/`
  - adidas Malaysia: `https://www.adidas.com.my/en`
  - lululemon Malaysia: `https://www.lululemon.com.hk/en-my/home`
  - ZALORA Singapore: `https://www.zalora.sg/`
  - ZALORA Indonesia: `https://www.zalora.co.id/s/sports`
  - ZALORA Malaysia: `https://www.zalora.com.my/`
  - ZALORA Philippines: `https://www.zalora.com.ph/`
