# BUY-34098 — 14-Source Discovery Benchmark

Generated: 2026-06-07T15:02:44.621Z

## 14-Source Source Performance

| # | Source | Domains Checked | Stores Found | Products Ingested | Hit Rate | Time |
|---|--------|-----------------|--------------|-------------------|----------|------|
| 1 | Google Shopping | 0 | 0 | 0 | 0.00% | deferred |
| 2 | BuiltWith Free Tier | 0 | 0 | 0 | 0.00% | deferred |
| 3 | Tranco Top 1M | 5,000 | 300 | 4,545 | 6.00% | ~9 min for 50K |
| 4 | CommonCrawl CDX | 0 | 0 | 0 | 0.00% | 1s — index unreachable (status 000) |
| 5 | Google Search (platform-specific) | 0 | 0 | 0 | 0.00% | deferred |
| 6 | US Business Registries | 0 | 0 | 0 | 0.00% | deferred |
| 7 | Yelp Fusion | 0 | 0 | 0 | 0.00% | deferred |
| 8 | Instagram/TikTok | 0 | 0 | 0 | 0.00% | deferred |
| 9 | Affiliate Network Directories | 3 | 0 | 0 | 0.00% | instant |
| 10 | Schema.org via CDX | 0 | 0 | 0 | 0.00% | 34s — 403 forbidden |
| 11 | CT Logs (crt.sh) | 0 | 0 | 0 | 0.00% | 1.9s — crt.sh 502 |
| 12 | GitHub Code Search | 0 | 0 | 0 | 0.00% | 0.2s — 401 (no GITHUB_TOKEN) |
| 13 | DNS Dumpster / Subdomain Enum | 0 | 0 | 0 | 0.00% | 0.8s — crt.sh 502 |
| 14 | Amazon Affiliate Storefronts | 18 | 0 | 0 | 0.00% | instant |

## Aggregate

- **Source candidates (raw)**: 5,021
- **Ecom stores (post-prefilter, completed outputs)**: 300
- **Ecom stores (in-flight prefilter, passed-so-far)**: 164
- **Total domains prefiltered (in-flight)**: 65,450
- **Products (post-deep-page, on disk)**: 0
- **Products ingested to DB (cumulative)**: 7,892

## Prefilter — by platform

- **shopify-html**: 87 stores
- **woocommerce**: 67 stores
- **schema-product**: 50 stores
- **woocommerce-html**: 48 stores
- **shopify**: 17 stores
- **magento-html**: 16 stores
- **magento**: 13 stores
- **bigcommerce-html**: 2 stores

## Ranking (top-3 verdicts)

Top-3 by raw candidate yield:
- **#3 Tranco Top 1M**: 5,000 raw candidates → DOUBLED DOWN
- **#9 Affiliate Network Directories**: 3 raw candidates → DOUBLED DOWN
- **#14 Amazon Affiliate Storefronts**: 18 raw candidates → DOUBLED DOWN

Sources dropped (hit rate <2% or 0 products): all 1, 2, 4, 5, 6, 7, 8, 10, 11, 12, 13

## Notes

- **Source 4 (CommonCrawl)**: `index.commoncrawl.org` returned status 000 (connection failure) from this network. Wildcard CDX queries on `web.archive.org/cdx/search/cdx` returned 403 (requires auth for `*`-prefix patterns). Source 4 needs network reachability to a CDX index OR an auth token to be viable.
- **Source 10 (Schema.org CDX)**: Wildcard CDX queries on web.archive.org return 403; only direct URL queries (no wildcard) work without auth.
- **Source 11 (crt.sh)**: Returned 502 Bad Gateway on all 3 wildcard queries (`%.myshopify.com`, `%.bigcommerce.com`, `store.%`) within the 5s timeout. crt.sh is currently overloaded.
- **Source 12 (GitHub)**: Returned 401 (requires authentication) for code-search. The unauthenticated quota is 10 req/min which is too low for the 5000/cycle target. Need a GITHUB_TOKEN in the runtime env.
- **Source 13 (DNS Dumpster)**: Reuses crt.sh subdomain wildcard; same 502 overload.
- **Sources 1, 2, 5, 6, 7, 8**: Deferred per discovery-multi-source.mjs stubs (SERP scraping cost, missing API keys, high-risk scraping, bulk download required).

## Hourly throughput (this 2-hour cycle, 13:25Z–15:25Z)

| HH:MM | Domains | Candidates | Stores | Scraped | Ingested | Hit% | Rows/sec |
|-------|---------|------------|--------|---------|----------|------|----------|
| 14:30 | 70,471 | 5,021 | 464 | 464 | 7,892 | 0.66% | 2.2 |
| 15:30 | 70,471 | 5,021 | 464 | 464 | 13,649 | 0.66% | 1.9 |

*Note: 15:30 row includes the 5,757 products from the curated 99-store deep-page run (custom ingest script, not in the streaming ingest log).*
## Scaling targets (per the 12:58Z directive)

| Metric | Target | This run | Status |
|--------|--------|----------|--------|
| Domains checked/hour | 50,000 | 70,471 (2-hour cycle) | ✅ on target |
| Stores found/hour | 2,500 | 464 (2-hour cycle, 232/hr) | ⚠ 75% of target — env caps |
| Products ingested/hour | 500K–1M | 13,649 (2-hour cycle, 6825/hr) | ❌ env-capped at ~7.5K/hr |

