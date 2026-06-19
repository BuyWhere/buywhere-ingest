# BUY-53283 Vietnam beauty follow-up lane

Date: 2026-06-19

## Scope

- Validate the three Vietnam beauty targets from `BUY-53268`.
- Record expected category and brand coverage.
- Identify the fastest ingestible merchant path from this workspace and call out blockers.

## Workspace context

- Existing reusable scraper coverage in this workspace is thin for this lane:
  - `src/scrapers/guardian_my.py`
  - `src/scrapers/guardian_sg.py`
- There is no current `watsons_*` or `sociolla_*` scraper here.
- That means `Guardian VN` has the clearest code-reuse path, but all three VN merchants still need net-new merchant work.

## Merchant assessment

### 1. Watsons Vietnam

- URL: `https://www.watsons.vn/en/`
- Market fit: keep
- Category coverage confirmed on the live site:
  - `Makeup`
  - `Skincare`
  - `Personal Care`
  - `Hair Care`
  - `Brands`
  - search-interest surfaces including `Suncare`, `Cleanser`, `Mascara`, `Eyeliner`, `Shampoo`, `Hair & Scalp treatment`, `Lips`, and `Body Wash`
- Brand coverage confirmed from current official brand pages:
  - `Cocoon`
  - `Lemonade`
- Why it matters:
  - Watsons Vietnam explicitly positions itself as a health-and-beauty retailer with trusted local and international brands.
  - The live site also calls out `K-Beauty`, `J-Beauty`, and global beauty trends, which makes it the broadest VN beauty recovery lane.
- Engineering read:
  - Good assortment fit, but the straightforward data path is not visible from simple HTTP fetches in this environment.
  - Category pages and the public site render in a browser, but direct endpoint probing showed a protected path rather than an obvious open catalog feed.
- Verdict:
  - Best broad-assortment VN lane.
  - Not obviously the fastest implementation lane from this environment.

### 2. Guardian Vietnam

- URL: `https://www.guardian.com.vn/`
- Market fit: keep
- Category coverage confirmed on the live site:
  - `Chăm Sóc Da Mặt` with `Tẩy trang`, `Sữa rửa mặt`, `Serum - Tinh chất`, `Mặt Nạ`, `Chống nắng`, and acne / eye-care branches
  - `Trang Điểm` with `Kem nền - BB Cream`, `Cushion`, `Che khuyết điểm`, `Son môi`, `Mascara`, and `Eyeliner`
  - `Chăm Sóc Cơ Thể`
  - `Chăm Sóc Tóc`
  - `Nước hoa`
  - `Tất Cả Thương Hiệu`
- Brand coverage confirmed on the live site:
  - `Dasique`
  - `Lanbena`
  - `Sace Lady`
  - `DODODOTS`
  - `Im Unau`
  - `OOTD`
- Why it matters:
  - Guardian VN has broad beauty depth across skincare, cosmetics, haircare, body care, and fragrance.
  - The site explicitly exposes both exclusive brands and detailed beauty taxonomy, which is enough to justify it as a serious recovery lane rather than a pharmacy-only add-on.
- Engineering read:
  - This is the most plausible fastest-ingestible VN lane because the workspace already has `guardian_my.py` and `guardian_sg.py`.
  - The merchant still appears to require anti-bot / browser-session handling from this environment, so reuse is architectural rather than drop-in.
- Verdict:
  - Best engineering starting point for VN beauty despite Watsons being slightly broader from a market-fit perspective.

### 3. Sociolla Vietnam

- URL: `https://vn.sociolla.com/`
- Market fit: keep
- Category coverage confirmed from live/search-visible product surfaces:
  - `makeup`
  - `skincare`
  - `hair`
  - `perfume`
  - beauty tools / applicators
- Brand and product signals confirmed from current search-visible pages:
  - `NOTE COSMETICS`
  - `Tangle Teezer`
  - `TOCOBO`
  - `TIA'M`
  - `Bifesta`
  - `Dearmay`
  - `Verites`
  - `Felce Azzurra`
- Why it matters:
  - Sociolla is the best specialist-beauty complement in VN and clearly covers beauty-first assortment rather than general health retail.
- Engineering read:
  - This is the hardest lane from the current environment.
  - The root site exposes a JavaScript-required shell, and direct fetches do not expose a clean catalog surface here.
- Verdict:
  - Strong specialist lane, but should stay third in implementation order.

## Fastest ingestible path

- Assortment-first order:
  - `Watsons VN` -> `Guardian VN` -> `Sociolla VN`
- Engineering-first order from this workspace:
  - `Guardian VN` -> `Watsons VN` -> `Sociolla VN`
- Recommendation:
  - Start with `Guardian VN` if the immediate goal is fastest live Vietnam beauty ingestion.
  - Keep `Watsons VN` as the next follow-up because it likely delivers the largest incremental beauty recovery once its protected catalog path is solved.
  - Leave `Sociolla VN` third because it appears to be the most JS-dependent / anti-bot-sensitive lane here.

## Blockers

### Shared blockers

- No existing Vietnam scraper implementation exists for these merchants in this workspace.
- All three merchants appear to need more than a plain static HTML fetch for reliable product extraction.

### Merchant-specific blockers

- `Guardian VN`
  - Reuse is promising, but the current environment hit anti-bot protection on direct endpoint probing.
  - Likely needs a browser session, solved cookies, or a validated catalog endpoint before `guardian_my.py`-style enumeration can be adapted.
- `Watsons VN`
  - Live browser-rendered category/navigation validation succeeded, but direct fetches did not expose an obvious public catalog payload.
  - Likely needs browser-network inspection or a protected client API path.
- `Sociolla VN`
  - Current environment sees a JS-required storefront shell and not a directly ingestible homepage catalog.
  - This is the clearest candidate for a rendered-browser scraper or a separate API-discovery step.

## Recommendation

- Keep all three VN merchants.
- Treat `Guardian VN` as the fastest realistic implementation lane from this codebase.
- Treat `Watsons VN` as the highest-value second lane for broad recovery.
- Treat `Sociolla VN` as a specialist-depth third lane after the renderer / anti-bot approach is proven.

## Sources checked on 2026-06-19

- Workspace:
  - `docs/buy-53268-beauty-sea-follow-up-2026-06-19.md`
  - `src/scrapers/guardian_my.py`
  - `src/scrapers/guardian_sg.py`
- Current web sources:
  - `https://www.watsons.vn/en/`
  - `https://www.watsons.vn/en/skincare/lc/0100000`
  - `https://www.watsons.vn/en/all-brands/lc/IgcBrands`
  - `https://www.watsons.vn/en/all-brands/b/20680/cocoon`
  - `https://www.watsons.vn/en/all-brands/b/20612/lemonade`
  - `https://www.guardian.com.vn/`
  - `https://vn.sociolla.com/`
  - current search-visible Sociolla VN product and brand pages surfaced from the official domain
