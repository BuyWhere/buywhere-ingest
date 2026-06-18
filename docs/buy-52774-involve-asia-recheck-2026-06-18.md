# BUY-52774 — Involve Asia approval re-check (2026-06-18T08:29Z)

**Wake:** BUY-52774 (origin: routine_execution `55b37d4a-b7f3-4afb-8843-6d1698471d98`)
**Agent:** Lyra (`bbfe3377-eb84-412f-9119-493d1732b4fd`)
**Parent:** [BUY-40848](/BUY/issues/BUY-40848) (Vera, `19dcd635`)
**Run time:** 2026-06-18T08:29:53Z

## Live probe

`POST https://powqjgbz.involve.asia/microservice/api/v1/authentication/login` returned **HTTP 200** with a valid `accessToken`. Account summary:

| field | value |
|---|---|
| `userId` | `1405276` |
| `email` | `signups@buywhere.ai` |
| `profileName` | `IA-Offer-Checking-4` |
| `status` | **`pending`** |
| `isKycNeeded` | `true` |
| `isAcceptTnc` | `false` |
| `isCompany` | `true` |
| `freezeToActive` | `false` |
| `createdAt` | `2026-06-11T06:54:41+00:00` |
| `x-ratelimit-remaining` | `199` (200/min quota intact — no lockout) |

Age at probe: **169h35m12s** since registration — past every escalation boundary (48h SLA / 72h escalation / 96h fallback / 120h board-routing / 168h collapse).

## Comparison to prior checks

| field | 2026-06-16T02:00Z (BUY-40848) | 2026-06-16T08:25Z (BUY-52269) | 2026-06-18T08:29Z (BUY-52774, this fire) | delta (vs BUY-52269) |
|---|---|---|---|---|
| `status` | `pending` | `pending` | `pending` | unchanged |
| `isKycNeeded` | `true` | `true` | `true` | unchanged |
| `isAcceptTnc` | `false` | `false` | `false` | unchanged |
| `freezeToActive` | — | `false` | `false` | unchanged |
| age (hours since createdAt) | 115.1h | 121.5h | 169.6h | +48.1h |

Account is still gated. Offer-application and deeplink-generation endpoints are not retried — they would 4xx against `status=pending`.

## Disposition

Cannot complete the original deliverable (apply for offer `4927`, generate deeplink) until the account flips to `active`. The dependency path is unchanged:

- **Internal unblock:** [BUY-51124](/BUY/issues/BUY-51124) — helpcentre escalation, owned by Vera, currently `in_review` waiting on board confirmation `639a20f1-772b-4cca-b614-7596aa7344c1` (created 2026-06-15T08:37:43Z, **still pending 72h+**) to send the support ticket
- **External unblock:** Involve Asia admin must activate the account or surface the missing KYC/TnC/business-verification step

`isAcceptTnc=false` is a small new signal worth flagging on the next helpcentre follow-up — the publisher TnC may not have been auto-accepted during signup, which is a self-serve path on `app.involve.asia` once the admin flips the freeze off. The freeze itself (`freezeToActive=false`) is admin-controlled.

## Action taken

- BUY-52774 updated to `blocked` with `blockedByIssueIds: [BUY-51124]`
- Comment posted with this evidence for the next routine fire
- No retry of the offer-application or deeplink-generation endpoints (would 4xx against `status=pending`)