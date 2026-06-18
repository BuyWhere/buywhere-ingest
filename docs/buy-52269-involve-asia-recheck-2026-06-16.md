# BUY-52269 — Involve Asia approval re-check (2026-06-16T08:25Z)

**Wake:** BUY-52269 (origin: routine_execution `55b37d4a-b7f3-4afb-8843-6d1698471d98`)
**Agent:** Lyra (`bbfe3377-eb84-412f-9119-493d1732b4fd`)
**Parent:** [BUY-40848](/BUY/issues/BUY-40848) (Vera, `19dcd635`)
**Run time:** 2026-06-16T08:25:23Z

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

Age at probe: **121h30m** since registration — well past the 48h SLA, 72h escalation, 96h fallback, and 120h board-routing mark.

## Comparison to prior check (BUY-40848, Vera, 2026-06-16T02:00:47Z)

| field | 2026-06-16T02:00Z | 2026-06-16T08:25Z | delta |
|---|---|---|---|
| `status` | `pending` | `pending` | unchanged |
| `isKycNeeded` | `true` | `true` | unchanged |
| `isAcceptTnc` | `false` | `false` | unchanged |
| age (hours since createdAt) | 115.1h | 121.5h | +6.4h |

Account is still gated. Offer-application and deeplink generation are not attempted — both endpoints reject `status=pending` accounts.

## Disposition

Cannot complete the original deliverable (apply for offer `4927`, generate deeplink) until the account flips to `active`. The dependency path:

- **Internal unblock:** [BUY-51124](/BUY/issues/BUY-51124) — helpcentre escalation, owned by Vera, currently `in_review` waiting on board confirmation `639a20f1-772b-4cca-b614-7596aa7344c1` to send the support ticket
- **External unblock:** Involve Asia admin must activate the account or surface the missing KYC/TnC/business-verification step

## Action taken

- BUY-52269 updated to `blocked` with `blockedByIssueIds: [BUY-51124]`
- Comment posted with this evidence for the next routine fire
- No retry of the offer-application or deeplink-generation endpoints (would 4xx against `status=pending`)
