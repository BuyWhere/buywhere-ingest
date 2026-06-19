# BUY-53257 Beauty SEA gap-fill targets

Date: 2026-06-19

## Why these lanes

- `BUY-53244` flagged Beauty as the top SEA zero-result gap at about 71%, with Indonesia and Thailand called out as near-zero coverage first.
- Local scraper inventory in this workspace already covers `guardian_sg.py`, but shows no existing Indonesia or Thailand beauty retailer lanes.

## Priority 1: Indonesia

### 1. Sephora Indonesia

- URL: `https://www.sephora.co.id/`
- Why: premium multi-brand lane with direct relevance to named misses from the report.
- Evidence:
  - Sephora Indonesia storefront currently markets "the world's most desired beauty brands".
  - Sephora Indonesia beautyfeed includes an SK-II launch/article, confirming live `SK-II` relevance on the market site.
  - Sephora Indonesia beautyfeed/article pages also surface `Charlotte Tilbury` pages in current search indexing.
- Expected coverage:
  - Premium skincare: `SK-II`, `La Mer`
  - Prestige makeup: `Charlotte Tilbury`
  - General premium beauty depth across skincare, makeup, fragrance, and haircare

### 2. Sociolla Indonesia

- URL: `https://www.sociolla.com/`
- Why: broad local-market beauty retailer with scale beyond prestige-only catalog.
- Evidence:
  - Sociolla homepage currently claims `400+ brand`.
  - Site structure exposes category and brand index pages suitable for merchant/category scraping.
- Expected coverage:
  - Long-tail Indonesia beauty assortment across skincare, cosmetics, personal care
  - Local and regional beauty brands that Sephora will miss
  - Stronger breadth for query recovery outside prestige-only searches

## Priority 1: Thailand

### 1. Sephora Thailand

- URL: `https://www.sephora.co.th/`
- Why: direct path to prestige brands already named in the zero-result report.
- Evidence:
  - Sephora Thailand storefront currently markets "the world's most desired beauty brands".
  - Current live product pages for `Charlotte Tilbury` are indexed on `sephora.co.th`, confirming live assortment.
- Expected coverage:
  - Prestige makeup: `Charlotte Tilbury`
  - Premium skincare and cosmetics depth
  - Strong overlap with named zero-result brands and brand-led beauty queries

### 2. EVEANDBOY Thailand

- URL: `https://www.eveandboy.com/`
- Why: high-scale Thailand beauty specialist for local-market breadth.
- Evidence:
  - EVEANDBOY homepage currently brands itself as `No.1 Beauty Retailer in Thailand`.
  - Store page currently lists `69 Stores`, which supports large active assortment and country relevance.
- Expected coverage:
  - Broad Thai-market cosmetics, skincare, fragrance, and beauty tools
  - Local Thai and Asian beauty brands missing from Sephora
  - Better recovery for non-prestige beauty search intents

### 3. Konvy Thailand

- URL: `https://www.konvy.com/`
- Why: online-first Thailand beauty marketplace with visible product depth.
- Evidence:
  - Current indexed Konvy product pages include beauty assortment at scale.
  - Search indexing shows `Dyson Airwrap` product/review presence, making it useful for the report's beauty-appliance miss.
- Expected coverage:
  - Beauty devices and tools, including `Dyson Airwrap`-type queries
  - Broad mid-market skincare and cosmetics
  - Additional assortment depth beyond Sephora and EVEANDBOY

## Priority 2 follow-up markets

- `MY`: Watsons MY, Guardian MY, Sephora MY
- `PH`: Watsons PH, SM Beauty, Look PH
- `VN`: Watsons VN, Guardian VN, Sociolla VN

## Recommended execution split

- Child 1: Indonesia beauty ingestion lane for `Sephora Indonesia` + `Sociolla`
- Child 2: Thailand beauty ingestion lane for `Sephora Thailand` + `EVEANDBOY` + `Konvy`
- Child 3: Follow-up backlog for MY/PH/VN once ID/TH execution is underway
