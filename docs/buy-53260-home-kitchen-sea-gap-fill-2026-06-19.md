# BUY-53260 Home/Kitchen SEA gap-fill targets

Date: 2026-06-19

## Why these lanes

- `BUY-53244` flagged Home/Kitchen as a P1 SEA zero-result gap at about `43%`, with `ID`, `TH`, `PH`, and `VN` called out as the thin markets.
- Reed's concrete misses were appliance- and cookware-led: `coffee maker`, `air fryer`, `Le Creuset`, and coffee-machine style searches that need merchant-direct kitchen assortment rather than generic marketplace spill.
- The workspace already shows Singapore-only appliance coverage through `src/scrapers/audio_house.py` and `src/scrapers/gain_city.py`; there is no comparable direct Home/Kitchen lane inventory here for Indonesia, Philippines, or Vietnam.

## Priority 1: Thailand

### 1. Power Buy Thailand

- URL: `https://www.powerbuy.co.th/en/category/small-appliance/kitchen-appliances`
- Why: strongest current Thailand appliance lane for the report's highest-frequency misses.
- Evidence:
  - Power Buy's live kitchen-appliance surface currently includes `air fryer` and `automatic drip coffee machine` assortment.
  - Current promo/category pages also expose `Tefal`, `Krups`, `Electrolux`, and `Ninja` kitchen-appliance inventory.
- Expected uplift:
  - Strongest TH recovery for appliance-led queries around `coffee maker`, `air fryer`, toaster ovens, and countertop kitchen electronics.
- Queries that should stop zeroing or materially improve:
  - `coffee maker`
  - `espresso machine`
  - `air fryer`
  - `toaster oven`

### 2. Central Online Thailand

- URL: `https://www.central.co.th/en/campaign/the-new-new-home`
- Why: best Thailand complement because it covers both premium cookware and higher-end kitchen appliances on one commerce surface.
- Evidence:
  - Current Central Online home campaign pages surface `Le Creuset`, fully automatic coffee machines, and oil-less/infrared air fryers.
  - Central also has a live `Le Creuset` Thailand storefront under `central.co.th`.
- Expected uplift:
  - Best TH path for premium cookware and named-brand recovery, especially where appliance-only merchants will miss `Le Creuset`.
- Queries that should stop zeroing or materially improve:
  - `Le Creuset`
  - `cast iron dutch oven`
  - `coffee machine`
  - `air fryer`

## Priority 1: Indonesia

### 1. Ruparupa / Informa

- URLs:
  - `https://www.ruparupa.com/informastore/c/elektronik.html`
  - `https://www.ruparupa.com/azko/brands/klaz/appliances.html`
- Why: best current Indonesia home-retail lane with visible kitchen-appliance breadth and cookware adjacency.
- Evidence:
  - Current Ruparupa/Informa listings include `air fryer` and `coffee maker` products.
  - Ruparupa's cookware/editorial surfaces also expose pot, pan, steamer, and pressure-cooker style assortment relevant to the Kitchen Warehouse analogue request.
- Expected uplift:
  - Immediate Indonesia recovery for mass-market appliance queries plus baseline cookware coverage.
- Queries that should stop zeroing or materially improve:
  - `coffee maker`
  - `air fryer`
  - `cookware set`
  - `pressure cooker`

### 2. Toko Tian Liong

- URL: `https://www.tianliong.co.id/`
- Why: strongest current Indonesia specialist kitchen-equipment lane and the closest local analogue to a Kitchen Warehouse-style merchant.
- Evidence:
  - Tian Liong currently describes itself as a long-running kitchen specialist with `13,000 SKUs`.
  - The live category structure exposes `Coffee & Barware`, `Kitchenware & Utensil`, and `Operating Equipment`.
- Expected uplift:
  - Better Indonesia coverage for cookware, kitchen tools, coffee prep, and specialty kitchen equipment that general home retailers under-index.
- Queries that should stop zeroing or materially improve:
  - `coffee grinder`
  - `coffee maker`
  - `cookware`
  - `kitchen utensils`

## Priority 2: Philippines

### 1. Abenson

- URL: `https://www.abenson.com/small-appliance`
- Why: best current Philippines appliance lane with both value and premium kitchen assortment.
- Evidence:
  - Current Abenson small-appliance pages surface `air fryer`, `breakfast maker`, and `coffee maker` assortment.
  - Abenson Home cookware pages also expose premium cookware like `Zwilling` and `Staub`.
- Expected uplift:
  - Strong PH recovery for appliance-led kitchen queries plus premium cookware adjacency.
- Queries that should stop zeroing or materially improve:
  - `coffee maker`
  - `air fryer`
  - `Staub`
  - `Zwilling cookware`

### 2. SM Home

- URLs:
  - `https://smhome.ph/collections/pots-and-pans`
  - `https://smhome.ph/collections/coffee-and-espresso-makers`
- Why: broad Philippines home-goods lane with direct cookware plus entry-level coffee and kitchen assortment.
- Evidence:
  - SM Home currently has live `pots and pans` and `coffee and espresso makers` collections.
  - Current listings include cast-iron pans, stainless cookware, and coffee makers.
- Expected uplift:
  - Better PH breadth on household cookware and non-premium kitchen essentials that Abenson may not carry deeply.
- Queries that should stop zeroing or materially improve:
  - `pots and pans`
  - `cast iron pan`
  - `coffee maker`
  - `sauce pan`

## Priority 2: Vietnam

### 1. Nguyen Kim

- URL: `https://www.nguyenkim.com/may-pha-ca-phe/`
- Why: best currently validated Vietnam electronics/appliance lane for coffee-machine and air-fryer style demand.
- Evidence:
  - Current Nguyen Kim pages show a live `may pha ca phe` commerce surface.
  - Current indexed Nguyen Kim appliance content also references `nồi chiên không dầu` products from brands like `Philips`, `Tefal`, and `Sunhouse`.
- Expected uplift:
  - Strongest VN recovery for appliance-led queries including coffee machines and air fryers.
- Queries that should stop zeroing or materially improve:
  - `coffee maker`
  - `espresso machine`
  - `air fryer`
  - `Philips air fryer`

### 2. LocknLock Vietnam

- URL: `https://www.locknlock.vn/`
- Why: clean Vietnam home-and-kitchen brand-direct lane that complements Nguyen Kim with cookware and kitchenware depth.
- Evidence:
  - LocknLock Vietnam currently operates a direct storefront plus a nationwide store page.
  - Current live content references air-fryer/microwave combination products and broader household kitchen catalog.
- Expected uplift:
  - Best VN complement for cookware, food-storage, tabletop, and branded home-kitchen recovery outside electronics-first merchants.
- Queries that should stop zeroing or materially improve:
  - `cookware set`
  - `air fryer`
  - `food container`
  - `kitchenware`

## Recommended execution split

- Child 1: Thailand home/kitchen lane for `Power Buy TH` + `Central Online TH`
- Child 2: Indonesia home/kitchen lane for `Ruparupa / Informa` + `Toko Tian Liong`
- Child 3: Philippines home/kitchen lane for `Abenson` + `SM Home`
- Child 4: Vietnam home/kitchen lane for `Nguyen Kim` + `LocknLock VN`

## Sources checked on 2026-06-19

- Workspace:
  - `src/scrapers/audio_house.py`
  - `src/scrapers/gain_city.py`
  - `src/scrapers/makro_pro_th.py`
  - `src/scrapers/lazada_th.py`
  - `src/scrapers/lazada_vn.py`
- Current web sources:
  - Power Buy TH
  - Central Online TH / Le Creuset TH surface
  - Ruparupa / Informa ID
  - Toko Tian Liong ID
  - Abenson PH
  - SM Home PH
  - Nguyen Kim VN
  - LocknLock VN
