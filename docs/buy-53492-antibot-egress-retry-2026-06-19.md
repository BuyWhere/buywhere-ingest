# BUY-53492 anti-bot egress retry

Date: 2026-06-19

## What changed

- Extended [src/scrapers/proxy_config.py](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/src/scrapers/proxy_config.py) so BrightData usernames can be built with shared `country` and `session` directives instead of hand-assembling `...-country-my-session-...` strings in ad hoc scripts.
- Added [scripts/buy53492_antibot_probe.py](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/scripts/buy53492_antibot_probe.py) to retry Watsons MY / Sephora MY through BrightData residential egress using both raw HTTP and Playwright.

## Verification

- Compile check:
  - `python3 -m py_compile src/scrapers/proxy_config.py scripts/buy53492_antibot_probe.py`
- Live probe:
  - `python3 scripts/buy53492_antibot_probe.py --output docs/buy-53492-antibot-probe-2026-06-19.json`

## Result

The anti-bot-capable residential egress is restored for direct HTTP/API retries:

| Target | HTTP via BrightData residential MY | Playwright via same proxy |
|---|---:|---:|
| `https://www.watsons.com.my/` | `200` | `403` |
| `https://api.watsons.com.my/` | `404` at origin, which proves the host is reachable | `403` |
| `https://www.sephora.my/` | `200` | `502` |
| `https://api.sephora.sg/` | `200` | `502` |

Notable implication:

- The previous conclusion that Watsons MY / Sephora MY were uniformly edge-blocked from this runtime is no longer true once the retry uses BrightData residential MY egress correctly.
- The remaining failure is narrower and browser-specific: Watsons still rejects the Playwright path, and Sephora returns `502` through Playwright while succeeding over raw HTTP.

## Next step

- Use the restored HTTP path first to enumerate Watsons OCC endpoints and Sephora storefront/API surfaces.
- Treat the Playwright failures as a separate browser-tuning problem rather than an egress-availability blocker.
