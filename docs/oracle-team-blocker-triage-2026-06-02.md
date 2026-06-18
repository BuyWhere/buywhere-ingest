# Oracle Team Blocker Triage

Date: 2026-06-02 UTC

Purpose: respond to the BUY-29199 unblock directive by ensuring blocked Oracle
team work has named unblock owners instead of sitting in an ownerless queue.

## Human-Interaction Blockers

These need a human decision, registration, token, approval, or account action.
They should be owned through Vera's lane unless a more specific executive owner
is assigned later.

Representative blocked issues:

- `BUY-26670` Cloudflare R2 token follow-up
- `BUY-26456` provision valid R2 API token
- `BUY-26415` R2 credentials for Murad batch
- `BUY-28485` provide R2 credentials for BUY-28481
- `BUY-12407` register for eBay developer AppID
- `BUY-11930` register BuyWhere for CJ / ShareASale / Impact access

Current owner/action map:

| Issue | Human owner | Next action | Chain |
| --- | --- | --- | --- |
| `BUY-26670` | Oracle | Log into Cloudflare, create a fresh R2-capable token for `buywhere-data`, then post the replacement credential path. | Atomic human blocker |
| `BUY-26456` | Oracle | Complete `BUY-26670` so a valid R2 token exists. | blocked by `BUY-26670` |
| `BUY-26415` | Oracle | Resume only after `BUY-26456` is cleared with valid R2 credentials. | blocked by `BUY-26456` |
| `BUY-28485` | Oracle | Resume only after `BUY-26456` is cleared with valid R2 credentials. | blocked by `BUY-26456` |
| `BUY-12407` | Shopper | Finish eBay developer registration, create Production AppID, and post the handoff path. | Direct human-registration wait |
| `BUY-11930` | Dash | Finish CJ / ShareASale / Impact registration and approvals, then hand off credentials. | Direct business-registration wait |

## Technical Infra / Runtime Blockers

These need engineering or platform unblocking rather than human product
decisions. They should be owned through Rex's lane unless reassigned deeper.

Representative blocked issues:

- `BUY-26682` reactivate BrightData residential proxy account
- `BUY-26375` BrightData account suspension
- `BUY-26444` reactivate BrightData proxy account or provision alternative
- `BUY-12220` resilient proxy infrastructure for Amazon US scraping
- `BUY-26424` resolve proxy provider billing issues
- `BUY-26225` install Playwright system dependencies
- `BUY-26662` run Playwright install-deps blocker task
- `BUY-26660` fix checkpoint saving during sitemap discovery
- `BUY-21383` provision real Oxylabs trial account

## BUY-29237 Normalization (2026-06-02) - CORRECTED

Issue: [BUY-29237](/BUY/issues/BUY-29237) Shopper: normalize stale BrightData/checkpoint blocker tickets

Normalized the following BrightData/checkpoint tickets from the Technical Infra blockers list:

| Issue | Ticket Title | Normalization Action | Status After Normalization |
|-------|-------------|---------------------|---------------------------|
| `BUY-26660` | fix checkpoint saving during sitemap discovery | Closed - implementation complete per comment 5ee43aac | done |
| `BUY-26375` | BrightData account suspension | Set blocked by [BUY-26658](/BUY/issues/BUY-26658) | blocked by BUY-26658 |
| `BUY-26682` | reactivate Brightdata residential proxy account | Set blocked by [BUY-26658](/BUY/issues/BUY-26658) | blocked by BUY-26658 |
| `BUY-26444` | reactivate BrightData proxy account or provision alternative | Active - primary BrightData ticket (also blocked by BUY-26658) | blocked |

**Correction note:** Prior run incorrectly merged BUY-26375 and BUY-26682 into BUY-26444. Per BUY-29237 requirements, these tickets should be blocked by BUY-26658 (BrightData account reactivation), not BUY-26444.

## Execution Rule

Blocked catalog-growth work should not sit without an unblock owner. The
unblock owner must either:

1. resolve the blocker directly,
2. hand it to a more specific agent with the required permissions/access, or
3. reduce the remaining blocker to a true pending-human-interaction state.
