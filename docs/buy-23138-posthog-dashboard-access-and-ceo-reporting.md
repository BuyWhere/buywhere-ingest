# BUY-23138 PostHog Dashboard Access And CEO Reporting

Date: 2026-05-28
Issue: BUY-23138
Project: PostHog `415112`

## Outcome

- Rex operational dashboard access: confirmed
- Lyra marketing dashboard access: confirmed
- Reed product dashboard access: blocked on missing dashboard artifact

## Dashboard Access Findings

### Rex operational dashboard

- Dashboard: `BuyWhere Observability`
- Dashboard id: `1560311`
- Evidence: returned by `GET /api/projects/415112/dashboards`, created by Richmond Teo
  (`richmond.teo@gmail.com`)
- Access conclusion: CEO access is confirmed because the CEO account is the creator and the dashboard
  already exists in the live project

### Lyra marketing dashboard

- Dashboard: `BuyWhere - Marketing Web Analytics (Canonical)`
- Dashboard id: `1622959`
- Evidence:
  - documented as canonical in `docs/posthog-marketing-analytics-audit.md`
  - returned by `GET /api/projects/415112/dashboards`, created by Richmond Teo
    (`richmond.teo@gmail.com`)
- Access conclusion: CEO access is confirmed because the CEO account is the creator and the
  canonical dashboard exists in the live project

### Reed product dashboard

- Dashboard expectation: product usage dashboard for the product KPI set described in
  `docs/posthog-product-analytics-spec.md`
- Live finding: no separate product usage dashboard appears in the current dashboard inventory for
  project `415112`
- Supporting evidence: `docs/posthog-product-analytics-spec.md` still says:
  - dashboard spec defined: yes
  - dashboard build confirmed live: no
- Blocker owner: Reed
- Blocker action: create the canonical product usage dashboard in PostHog from the defined KPI spec,
  then confirm CEO visibility against that live dashboard artifact

## Daily CEO Report Wiring

The reporting path is already live and uses PostHog-backed inputs:

- Reed input package: `docs/daily-ceo-report-input-2026-05-26.md`
- Rex input package: `docs/daily-ceo-report-input-2026-05-26-rex.md`
- Lyra input package: `docs/daily-ceo-report-input-2026-05-26-lyra.md`
- Published CEO reports:
  - `docs/daily-ceo-report-2026-05-27.md`
  - `docs/daily-ceo-report-2026-05-28.md`

Current wiring conclusion:

- Rex metrics are already feeding the Daily CEO Report through the dated Rex input package
- Lyra marketing metrics are already feeding the Daily CEO Report through the canonical marketing
  dashboard logic and dated Lyra input package
- Reed product metrics are feeding the Daily CEO Report through direct PostHog query packages today,
  but the dedicated product dashboard artifact itself is still missing
