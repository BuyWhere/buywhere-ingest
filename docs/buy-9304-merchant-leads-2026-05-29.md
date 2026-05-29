# BUY-9304 Merchant Hunt

Date checked: 2026-05-29 UTC

Method:
- Queried search-engine indexed `wp-json` pages that exposed WooCommerce Store API routes.
- Validated each candidate live with `GET /wp-json/wc/store/v1/products?per_page=1`.
- Kept only stores that returned public product JSON during this heartbeat.

Validated open WooCommerce Store API merchants:

| Domain | Evidence from live Store API check |
| --- | --- |
| `megagop.com` | Returned product JSON; first item had blank `name` but `short_description` was `GOP Flag Ceramic Coffee Mug, 11 oz.` |
| `entranceaccess.com` | Returned `Sectec AISI 304 Horizontal & Vertical Brushed Hygiene` |
| `y2sth.com` | Returned `Y2S BOOST UP + ESSENCE + CLEAR SPOT SET ...` |
| `aboveaveragegolf89.com` | Returned `Launch Monitor Session At Your Local Driving Range` |
| `dysfunctionalshoes.com` | Returned `HANNES - PY WHITE BROWN` |
| `ghcpk.com` | Returned `Headphone` |
| `raycowylie.com` | Returned `33D4000 - Replacement i4000 Display (Pre-Configured)` |
| `authorkimann.com` | Returned `Ten Little Axolotls` |
| `earthstayer.com` | Returned `Terrestrial SP (Fulvic Acid Soluble Powder)` |

Borderline candidate:

| Domain | Result |
| --- | --- |
| `foreveryoung8298.com` | Endpoint responded, but output was polluted by a PHP notice before JSON, so I did not count it as a clean open lead. |

Rejected during validation:
- `pushcomponents.com`: Cloudflare challenge page.
- `petsep.com`: 404 on the direct products endpoint during this check.
- `techtrivial.com`: 406 / ModSecurity block.
- `formula7.ru/shop`: 403.

Notes:
- These checks were live and date-specific. Store API exposure can change quickly if a merchant adds WAF rules or plugin updates.
- The list is ready for pipeline enrichment or a follow-on pass that adds geography, category, contact paths, and traffic estimates.
