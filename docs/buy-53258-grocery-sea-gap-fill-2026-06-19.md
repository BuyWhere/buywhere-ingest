# BUY-53258 Grocery SEA gap-fill targets

Date: 2026-06-19

## Why these lanes

- `BUY-53244` flagged Grocery as the second P0 SEA zero-result gap at about 52%, with Indonesia, Thailand, and Vietnam called out as the thin markets.
- The report's concrete symptom is still severe under-coverage: Thailand was cited at `901` grocery products and Indonesia at `1,216`, which is too small for branded grocery queries to recover reliably.
- A prior TH grocery wave (`BUY-31616`) closed as done on 2026-06-09, but the 2026-06-19 report still shows TH as under-covered, so this cycle needs a fresh TH-first execution wave rather than treating the prior task as sufficient.

## Priority 1: Thailand

### 1. Tops Online Thailand

- URL: `https://www.tops.co.th/en`
- Why: direct supermarket lane with the clearest grocery depth signal in-market.
- Evidence:
  - Tops Thailand currently markets `40,000+` items online.
  - The storefront exposes fresh food, pantry, beverages, and grocery brand/category pages.
  - Current live brand pages on Tops include `NESCAFE`, which makes it a direct fit for brand-led grocery search recovery.
- Expected uplift:
  - Directional estimate: `+20K to +35K` TH grocery SKUs after overlap/dedup.
  - Strongest recovery on pantry, beverages, snacks, dairy, and household consumables.
- Queries that should stop zeroing or materially improve:
  - `nescafe gold`
  - `ground coffee`
  - `instant noodle`
  - `olive oil`

### 2. Makro PRO Thailand

- URL: `https://www.makro.pro/en`
- Why: broad TH wholesale grocery lane with dry grocery, fresh, and business-supply depth that complements Tops rather than duplicating it entirely.
- Evidence:
  - Makro PRO currently advertises raw materials, fresh products, dry products, and complete-product delivery.
  - The site exposes grocery and ready-to-eat category trees.
  - Makro PRO has a live `NESCAFE` collection page with product depth already visible.
- Expected uplift:
  - Directional estimate: `+15K to +30K` TH grocery SKUs after overlap/dedup.
  - Best fit for bulk pantry items, beverages, foodservice staples, and dry goods breadth.
- Queries that should stop zeroing or materially improve:
  - `nescafe`
  - `coffee sachets`
  - `instant noodle`
  - `cooking oil`

### 3. Lazada Thailand grocery / LazMart

- URL: `https://www.lazada.co.th/tag/lazmart/`
- Why: marketplace fallback and commercial-scale breadth for TH if merchant-direct lanes do not close the gap quickly enough.
- Evidence:
  - Lazada TH currently exposes a LazMart shopping surface.
  - Grocery-adjacent TH product pages are live for `NESCAFE`, milk, and other packaged-food items.
- Expected uplift:
  - Directional estimate: `+25K to +50K` TH grocery SKUs if routed as a marketplace ingestion or partnership lane.
  - Highest raw breadth, but also highest normalization and marketplace-quality overhead.
- Queries that should stop zeroing or materially improve:
  - `nescafe gold`
  - `milk`
  - `instant noodle`
  - `snacks`

## Priority 2: Indonesia

### 1. Alfagift / Alfamart Online

- URL: `https://alfagift.id/`
- Why: broad national online-grocery lane with strong relevance to everyday branded grocery searches.
- Evidence:
  - Alfagift currently positions itself as a complete online grocery destination in Indonesia.
  - The site exposes food, beverages, cooking ingredients, household, baby, health, and personal-care categories.
  - Live `Indomie` product and brand pages are indexed now.
- Expected uplift:
  - Directional estimate: `+10K to +20K` ID grocery SKUs after overlap/dedup.
  - Good fit for packaged foods, drinks, pantry staples, and convenience-store grocery brands.
- Queries that should stop zeroing or materially improve:
  - `indomie`
  - `instant noodle`
  - `ground coffee`
  - `cooking oil`

### 2. Klik Indomaret

- URL: `https://www.klikindomaret.com/`
- Why: second large Indonesia convenience-grocery lane that should deepen national CPG coverage beyond Alfagift.
- Evidence:
  - Current category pages span food, kitchen/cooking ingredients, drinks, household, health, and personal care.
  - The site is already recognized in our discovery inputs as an Indonesia market candidate.
- Expected uplift:
  - Directional estimate: `+8K to +15K` ID grocery SKUs after overlap/dedup.
  - Strong complement to Alfagift on staple grocery and convenience assortment.
- Queries that should stop zeroing or materially improve:
  - `indomie goreng`
  - `instant coffee`
  - `soy sauce`
  - `rice`

## Priority 3: Vietnam

### 1. Bách hoá XANH

- URL: `https://www.bachhoaxanh.com/`
- Why: strongest currently validated VN grocery lane in this cycle, with visible product breadth and branded food pages.
- Evidence:
  - Current site messaging advertises `15,000` products and `2h` delivery.
  - The site exposes a wide grocery category tree and live `Omachi` instant-noodle product pages.
- Expected uplift:
  - Directional estimate: `+10K to +15K` VN grocery SKUs after overlap/dedup.
  - Best fit for food staples, drinks, packaged foods, and household grocery recovery.
- Queries that should stop zeroing or materially improve:
  - `omachi`
  - `instant noodle`
  - `fish sauce`
  - `ground coffee`

### 2. Co.op Online Vietnam

- URL: `https://cooponline.vn/danh-muc-san-pham-app-live`
- Why: supermarket-style VN lane with breadth across fresh, frozen, drinks, dairy, pantry, and baby products.
- Evidence:
  - Current product-category pages show meat/eggs/seafood, processed food, frozen/chilled, snacks, dairy, drinks, pantry staples, and baby products.
- Expected uplift:
  - Directional estimate: `+5K to +10K` VN grocery SKUs after overlap/dedup.
  - Lower certainty than Bách hoá XANH, but clearly useful as a follow-on VN expansion lane.
- Queries that should stop zeroing or materially improve:
  - `milk`
  - `rice`
  - `fish sauce`
  - `instant noodle`

## Recommended execution split

- Child 1: TH merchant-direct grocery ingestion wave for `Tops Online TH` + `Makro PRO TH`
- Child 2: TH platform/commercial route for `Lazada TH / LazMart grocery`
- Child 3: ID grocery ingestion wave for `Alfagift` + `Klik Indomaret`
- Child 4: VN grocery ingestion wave for `Bách hoá XANH` + `Co.op Online`

## Notes on estimates

- SKU-uplift estimates are directional planning numbers, not committed landed counts.
- The estimates assume normal overlap between supermarkets/marketplaces and some loss from normalization, deduplication, inactive products, and non-grocery spill.
- The branded query targets are inferred from live merchant category/brand evidence and the weekly gap report's grocery failure pattern; the execution children should verify exact basket/query recovery once the first batches land.
