# BUY-53268 Beauty SEA follow-up lanes

Date: 2026-06-19

## Scope

- Validate the second-wave SEA beauty targets for `MY`, `PH`, and `VN`.
- Record which merchants are currently live and category-fit for beauty recovery.
- Stage follow-up execution only after the higher-priority ID/TH lanes (`BUY-53266`, `BUY-53267`) are complete or a human explicitly assigns extra capacity.

## Workspace context

- Current local scraper inventory in this workspace only shows `src/scrapers/guardian_sg.py` for beauty retail; there are no MY/PH/VN beauty-direct lanes already prepared here.
- That means second-wave execution will likely require net-new merchant work rather than simple reuse of an existing country scraper.

## Malaysia

### 1. Watsons Malaysia

- URL: `https://www.watsons.com.my/`
- Keep: yes
- Why:
  - Watsons Malaysia explicitly presents itself as a leading health-and-beauty retailer with `750+` stores nationwide.
  - The current site navigation exposes core beauty categories directly: `Skincare`, `Makeup`, `Hair Care`, and `Brands`.
  - Watsons also states that it carries Korean, Japanese, Chinese, and local Malaysian beauty brands, which makes it the best broad-market MY recovery lane.
- Best for:
  - Mass-market skincare, makeup, haircare, and personal care
  - Broad beauty query recovery beyond prestige-only brands

### 2. Sephora Malaysia

- URL: `https://www.sephora.my/`
- Keep: yes
- Why:
  - Sephora Malaysia is live and exposes deep beauty-specific navigation across `Makeup`, `Skincare`, `Hair`, `Tools & Brushes`, `Bath & Body`, and `Fragrance`.
  - Current indexed pages confirm live Malaysia-market product surfaces for `Charlotte Tilbury` and `La Mer`.
  - This is the cleanest MY lane for prestige recovery tied to the original zero-result misses.
- Best for:
  - Prestige makeup and skincare
  - Named-brand recovery like `Charlotte Tilbury` and `La Mer`

### 3. Guardian Malaysia

- URL: `https://www.guardian.com.my/`
- Keep: yes
- Why:
  - Guardian Malaysia is live and currently markets skincare, cosmetics, personal care, and pharmacy categories on the main store surface.
  - It is a good Watsons complement for broad health-and-beauty depth and should improve mid-market skincare / cosmetics recovery.
- Best for:
  - Mid-market beauty breadth
  - Everyday skincare, cosmetics, personal care, and fragrance

### Malaysia recommendation

- Execution order: `Watsons MY` -> `Sephora MY` -> `Guardian MY`
- Reason:
  - Watsons gives the best broad recovery.
  - Sephora adds the prestige brands the report explicitly called out.
  - Guardian is useful but somewhat duplicative with Watsons, so it is the third lane if capacity is tight.

## Philippines

### 1. Watsons Philippines

- URL: `https://www.watsons.com.ph/`
- Keep: yes
- Why:
  - Watsons Philippines is live and exposes `Skincare`, `Hair`, `Fragrance`, `Makeup`, `All Brands`, and `K-Beauty` on the current site.
  - This is the strongest broad PH beauty lane for immediate online coverage.
- Best for:
  - Mass-market skincare, makeup, fragrance, and K-beauty recovery

### 2. LOOK At Me Philippines

- URL: `https://www.lookatme.com.ph/`
- Keep: yes
- Why:
  - LOOK At Me is live and explicitly positions itself around premium / rare / cult beauty.
  - The current site exposes beauty-first navigation across `Makeup`, `Skin Care`, `Hair`, `Tools & Brushes`, `Bath & Body`, `Fragrance`, `Wellness`, and `Brands`.
  - This is the best PH complement for premium and enthusiast beauty assortment that Watsons may under-index.
- Best for:
  - Premium and niche beauty
  - Higher-value makeup, skincare, and fragrance queries

### 3. SM Beauty

- URL: `https://www.smbeauty.com/`
- Keep: conditional / secondary
- Why:
  - The brand is clearly active in-market, but the direct ecommerce surface is currently anti-bot protected from this environment.
  - Third-party current market coverage still shows SM Beauty counters carrying global beauty brands inside SM retail locations, which supports offline relevance.
  - Because the direct online surface could not be cleanly validated here, it should not be the first PH ingestion target.
- Best for:
  - Secondary PH expansion after Watsons PH and LOOK At Me
  - Possible offline-to-online brand breadth if a workable commerce surface is confirmed later

### Philippines recommendation

- Execution order: `Watsons PH` -> `LOOK At Me PH`
- Hold:
  - `SM Beauty` stays as a reserve lane until a directly ingestible commerce surface is confirmed.

## Vietnam

### 1. Watsons Vietnam

- URL: `https://www.watsons.vn/en/`
- Keep: yes
- Why:
  - Watsons Vietnam is live and positions itself as an online health-and-beauty store.
  - The current site messaging highlights beauty innovation and a wide range of authentic beauty and health products.
  - This is the cleanest broad VN beauty lane.
- Best for:
  - Broad-market skincare, makeup, personal care, and imported beauty trends

### 2. Guardian Vietnam

- URL: `https://www.guardian.com.vn/`
- Keep: yes
- Why:
  - Guardian Vietnam states that it carries `500+` health-and-beauty brands and `10,000+` items across beauty and wellness categories.
  - The current Vietnam positioning explicitly calls out sections for cosmetics, skincare, body care, and health.
  - This is the strongest VN complement for breadth beyond Watsons alone.
- Best for:
  - Broad skincare / cosmetics depth
  - General-market beauty recovery at scale

### 3. Sociolla Vietnam

- URL: `https://vn.sociolla.com/`
- Keep: yes
- Why:
  - The official VN Sociolla surface is live and describes itself as a channel for authentic beauty products with nationwide delivery.
  - Current market references continue to associate Sociolla Vietnam with makeup, skincare, hair treatment, and perfume.
  - This is the best VN follow-up lane for beauty-specialist depth beyond pharmacy-led chains.
- Best for:
  - Beauty-specialist assortment
  - Skincare, makeup, haircare, and fragrance depth

### Vietnam recommendation

- Execution order: `Watsons VN` -> `Guardian VN` -> `Sociolla VN`
- Reason:
  - Watsons + Guardian cover the broadest immediate market.
  - Sociolla adds specialist depth and should be the third lane once core VN breadth is underway.

## Recommended execution split

- Child 1: Malaysia beauty lane for `Watsons MY` + `Sephora MY` + `Guardian MY`
- Child 2: Philippines beauty lane for `Watsons PH` + `LOOK At Me PH`
- Child 3: Vietnam beauty lane for `Watsons VN` + `Guardian VN` + `Sociolla VN`

## What not to do yet

- Do not open active execution on these follow-up lanes while `BUY-53266` and `BUY-53267` are still the first-wave priority.
- Do not make `SM Beauty` a first PH scraper target until a directly ingestible ecommerce path is confirmed.

## Sources checked on 2026-06-19

- Workspace:
  - `src/scrapers/guardian_sg.py`
  - `docs/buy-53257-beauty-sea-gap-fill-2026-06-19.md`
- Current web sources:
  - `https://www.watsons.com.my/who_we_are`
  - `https://www.watsons.com.my/b/brandlist`
  - `https://www.sephora.my/`
  - `https://www.guardian.com.my/`
  - `https://www.watsons.com.ph/`
  - `https://www.lookatme.com.ph/`
  - `https://www.watsons.vn/en/`
  - `https://www.guardian.com.vn/guardian/gioi-thieu`
  - `https://vn.sociolla.com/`
