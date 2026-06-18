# BUY-51042 — Daily GSC Indexing API push 2026-06-15

**Issue:** BUY-51042 (Daily GSC Indexing API push — submit working URLs)
**Heartbeat:** 2026-06-15 ~07:30–07:51Z
**Routine:** 147a30b6-50b0-4bac-8af0-071d07395d90
**Comment posted:** 1a69faf7-a474-430f-9dbf-1bc8d6bfa57d (on BUY-51042)

## Submission summary

| Metric | Value |
|---|---|
| Sitemaps submitted | 5 (pages, categories, compare, products, products-sg) |
| URLs in sitemaps (unique) | 242 (pages 214, categories 28, compare 0, products 0) |
| Net-new vs yesterday | 100 |
| Submitted to Indexing API | 100/100 (URL_UPDATED) |
| Daily quota used | 100/200 (50% headroom) |
| Quality gate (10 spot-check) | 10/10 returned HTTP 200 |
| Deindex needed | 0 |
| Coverage on 20-URL sample | 7 indexed, 10 discovered-not-indexed, 1 redirect, 1 unknown, 1 crawled-not-indexed |

## Submission composition

- 83 best-* guide pages (programmatic, BUY-45793 pipeline)
- 17 cheapest-* + iphone/laptop/macbook/smartphone/gaming US/landing pages

## Sitemap durability flags (still broken)

- **sitemap-products.xml** = empty urlset (0 URLs). Same as prior heartbeats.
- **sitemap-products-sg.xml** = HTTP 410 Gone. Same as prior heartbeats.
- **Durable fix:** BUY-22586 (catalog→sitemap pipeline, Dash). Daily push band-aids by submitting working URLs anyway.

## Weekly KPIs (Mon cadence — would be posted on BUY-22685)

- Indexed pages with impressions (28d): 15 distinct URLs (homepage + blog/best-* + a few categories)
- Top clicks (28d): homepage 20, blog/best-laptop-deals-singapore 6, blog/best-price-tracking-tools 4
- Goal progress: 15/50,000 indexed pages (0.03%) — Workstream A. 17 days to 2026-06-30.

## Note on BUY-22685 metrics post

Per memory BUY-35384 pattern, BUY-22685 is parent-locked and `?identifier=` and `?search=` filters on `/api/companies/{id}/issues` are both silently ignored (verified 2026-06-15T07:43Z). The Mon metrics were captured in the BUY-51042 comment (id 1a69faf7) for the next CEO rollup.

## Acceptance

- [x] 100/100 Indexing API submissions accepted
- [x] 10/10 quality-gate URLs returned 200
- [x] No new soft-404 / non-200 issues introduced
- [ ] WoW growth in distinct URLs observed — not yet measurable at this scale
