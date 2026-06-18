# BUY-52573: Daily Competitor Intelligence Digest — 2026-06-18

Date: 2026-06-18 UTC (01:02Z fire, 01:10Z write)
Issue: [BUY-52573](/BUY/issues/BUY-52573)
Parent: [BUY-7445](/BUY/issues/BUY-7445) (Daily community monitoring for competitor intelligence pipeline)
Routine: Reed daily digest (status: completed for today)
Status: daily digest generated

## Executive Summary

Daily monitoring of AI-agent commerce competitive landscape. Sources: Hacker News (live, HN Algolia — 7-day window), GitHub trending (live, 1-day window). Product Hunt and Smithery MCP directory remained blocked (no API token / 404 endpoint).

| Threat Level | Count | Δ vs 2026-06-16 |
|---|---:|---:|
| Critical | 8 | +2 |
| High | 20 | 0 |
| Medium | 12 | 0 |
| Monitor | 32 | -1 |
| **Total** | **72** | **+1** |

Platform mix: GitHub 38 (▲2), Hacker News 34 (▼1), Product Hunt 0 (blocked), Smithery 0 (404).

**Day-over-day read:** Flat-to-up day — total signal count essentially unchanged from 2026-06-16 (72 vs 71). The day-over-day bump is two new critical-tier items, both n8n-related (the johnisanerd `n8n-nodes-google-shopping-api` + `n8n-nodes-yahoo-shopping-api` repos). **The headline strategic shift: the Visa+OpenAI story has aged out of the HN 7-day window for the first time in 9 days** — yesterday's AP News (5pt) + WSJ (2pt) submissions are no longer in scope. The "Visa plugs payment network into ChatGPT" cycle is now closed as a live HN signal and **reclassifies from "active strategic watch" to "background context"** in the weekly tier list. No replacement top-of-mind strategic story surfaced today; HN high-tier is empty (only 2 medium-tier keyword matches: Spanly and "Building a Stateful AI Agent"). **The day's real new entrant signal is on GitHub, not HN** — three new 1★ agentic-commerce repos and a confirmed n8n+shopping-API cohort.

## API Health

| Platform | Status | Notes |
|---|---|---|
| Hacker News (Algolia) | LIVE | 7-day window, 11 named-competitor keywords, deduplicated by `objectID` |
| GitHub Search | LIVE | 1-day window, 4 commerce keywords, unauthenticated (60 req/h cap respected) |
| Product Hunt | BLOCKED | `PH_API_TOKEN` env var not set in this workspace |
| Smithery MCP | BLOCKED | `https://smithery.ai/api/mcp` returns 404 (endpoint removed) |

## Top Strategic Signals (HN, ranked by reach)

1. **No new high-impact HN stories in the last 24h.** HN high-tier is empty today. The two medium-tier keyword matches (both 1–2pt, generic AI/MCP content, no commerce relevance) are:
   - **Show HN: Spanly — See what AI agents do inside your MCP server** ([spanly.com, 1pt / 2c](https://spanly.com/)) — *Medium (tracked, carried).* MCP analytics. Same signal as the last four digests; traction held at 1pt, +1 comment in 24h.
   - **Show HN: Building a Stateful AI Agent** ([centri, 2pt / 0c](https://github.com/surya17495/centri)) — *Medium (NEW today).* Generic stateful-agent pattern, keyword match on "agent commerce". No commerce relevance.

2. **Visa+OpenAI story has aged out of HN 7-day window (first time in 9 days).** The AP News (5pt, 2026-06-10) and WSJ (2pt, 2026-06-12) submissions that anchored the 06-13/14/15/16/17 briefs are no longer in the HN Algolia 7-day window. **Reed strategic read:** the "Visa plugs payment network into ChatGPT" story has run its HN cycle. **It is no longer an "active signal" — reclassify to background context in the weekly tier list.** No fresh strategic replacement surfaced today.

3. **High-engagement HN noise (monitor tier, false positives).** "Buy for Me" substring continues to over-trigger on unrelated content — Launch HN: Adam (YC W25) 149pt, Show HN: VoiceDraw 47pt, Show HN: Sabela (Haskell) 44pt, etc. None are commerce. Listed for completeness under Monitor; ignore for product strategy.

**Reed strategic read:** Today is a **strategically quiet day** for HN. No new competitor story to escalate. The day's action items are all on the GitHub side (see Critical + High-tier sections below).

## Critical GitHub Threats

| # | Repo | Author | Stars | Notes |
|---|---|---|---:|---|
| 1 | **n8n-nodes-google-shopping-api** | [johnisanerd](https://github.com/johnisanerd/n8n-nodes-google-shopping-api) | 0★ | **n8n community node for the Google Shopping API (Apify-backed): search products and return prices, sellers, ratings, and product images.** |
| 2 | **n8n-nodes-yahoo-shopping-api** | [johnisanerd](https://github.com/johnisanerd/n8n-nodes-yahoo-shopping-api) | 0★ | **n8n community node for the Yahoo Shopping API on Apify.** Search products with prices, sellers, images; filter by price range. |
| 3 | **AI-Shopping-Assistant-n8n-Gemini-Groq-Python** | [TAMBESANTOSH077](https://github.com/TAMBESANTOSH077/AI-Shopping-Assistant-n8n-Gemini-Groq-Python) | 0★ | Built an AI-powered Telegram shopping assistant for personalized product recommendations. Integrated voice-to-text, Gemini/Groq LLMs, n8n workflow orchestration, and Python backend. |
| 4 | E-comm-React | [jnanaprasanna-22](https://github.com/jnanaprasanna-22/E-comm-React) | 0★ | Responsive e-commerce web application using React.js, React Router, Context API. Tutorial-grade. |
| 5 | Springboot-Ecommerce-Backend-CRUD-and-Search-Feature | [VASUSINH](https://github.com/VASUSINH/Springboot-Ecommerce-Backend-CRUD-and-Search-Feature) | 0★ | RESTful e-commerce backend using Spring Boot + JPA + H2. Tutorial-grade. |
| 6 | aforro-backend-assignment | [shattakshi](https://github.com/shattakshi/aforro-backend-assignment) | 0★ | Django REST API backend — product search, inventory management, order processing, Redis rate limiting, Celery. Tutorial-grade. |
| 7 | Market-Track-Monitoring-Cost-changes-across-Agriculture-product-channels | [Nivash-M-K](https://github.com/Nivash-M-K/Market-Track-Monitoring-Cost-changes-across-Agriculture-product-channels) | 0★ | "BookStore App" mislabeled repo; actual subject is monitoring cost changes across agricultural product channels. Low threat. |
| 8 | Admin-Dashboard-Application | [adityayadav20048-ace](https://github.com/adityayadav20048-ace/Admin-Dashboard-Application) | 0★ | Next.js + MUI + Zustand admin dashboard. Tutorial-grade. |

**Read:** The critical tier is again dominated by generic e-commerce templates (6 of 8 are tutorial repos). **The strategic signal here is the n8n cohort (items 1, 2, 3).** Three repos — all created today, all wrapping a price-comparison API (Google Shopping, Yahoo Shopping, or combining LLM+Telegram+n8n) — confirm that **the developer community is actively building n8n nodes around shopping APIs and AI shopping assistants.** This **directly supports the pending "File child for n8n BuyWhere node" action item from the 2026-06-13/14/15/16 briefs** — independent third-party repos prove the developer demand side. **Reed recommendation: promote the n8n BuyWhere node child from "pending fold-in to next weekly brief" to "file as a dedicated child this week."** Within Reed's authority to file the child; the implementation work itself would route to Rex or Bolt.

## High-Threat GitHub Projects (selected, 20 total)

Selected for having "agentic commerce", "x402 onchain", or "n8n commerce" framing rather than just "shopping API" keyword match:

### 1★ (3 new today — all agentic-commerce variants)

- **grocery-deals-agent** ([Parikshit00/grocery-deals-agent](https://github.com/Parikshit00/grocery-deals-agent)) — **1★**, "Agentic AI assistant that finds grocery discounts, optimizes shopping lists, and searches supermarket offers in Germany." *Vertical (grocery) + geography (Germany) + agentic framing. Consumer-side overlap with BuyWhere's multi-merchant comparison story. Watch 30 days — early traction at 1★.*
- **steel-mem0-cookbook** ([steel-experiments/steel-mem0-cookbook](https://github.com/steel-experiments/steel-mem0-cookbook)) — **1★**, "Steel x mem0 collab cookbook — a shopping agent that remembers durable preferences across merchants." *Multi-merchant memory agent. Steel is browser-auth-as-a-service; mem0 is the persistent memory layer. The combination is a credible agentic-commerce stack — bookmark for the next Reed product strategy review.*
- **webaz** ([webaz-protocol/webaz](https://github.com/webaz-protocol/webaz)) — **1★**, "WebAZ — agent-native decentralized commerce protocol." *Yet another "agentic-commerce protocol" framing, this time with the decentralized angle explicit. The naming cohort (agentic-commerce-kit + webaz + ace + pfn-hedera-commerce-agent + agent-commerce-hub-cobo-hackathon) is now 5+ distinct onchain/decentralized agentic-commerce repos in 7 days.*

### 0★ (17 today, agentic-commerce-framed)

- **agent-commerce** ([Kubudak90/agent-commerce](https://github.com/Kubudak90/agent-commerce)) — "Turn an AI agent into an Arcorapay merchant — sell from a catalog and invoice in USDC, payable cross-chain from Base via x402." *Adds another x402 payment-rail variant to the cohort (now 5+). x402 is now the de facto payment-rail default for new agentic-commerce prototypes.*
- **agent-readiness-mcp** ([forgemeshlabs/agent-readiness-mcp](https://github.com/forgemeshlabs/agent-readiness-mcp)) — "MCP server that audits websites for AI agent readiness across discovery, trust, commerce, interoperability, Google AI Se[arch]..." *The "AI agent readiness" framing is a new subcategory — peer to AEO (Answer Engine Optimization). Watch as a peer-watch item; if a BuyWhere "agent-readiness audit" page were created, it could capture this search intent.*
- **aso-score-mcp** ([forgemeshlabs/aso-score-mcp](https://github.com/forgemeshlabs/aso-score-mcp)) — "MCP server that calculates an Agent Signal Optimization score across discovery, trust, commerce, interoperability, Google AI..." *Companion repo from the same author — together agent-readiness-mcp + aso-score-mcp form a "score your site for AI agent fitness" offering. Same author (forgemeshlabs) building both halves of the loop.*
- **agentic-commerce-kit** ([nick-liyao/agentic-commerce-kit](https://github.com/nick-liyao/agentic-commerce-kit)) — "AI-agent readiness audits and MCP-ready commerce utilities for Shopify and ecommerce stores." *Direct overlap with the agent-readiness-mcp framing above — second author in 24h building the same concept for Shopify/ecommerce.*
- **aster-commerce-os** ([atlasbuilds77/aster-commerce-os](https://github.com/atlasbuilds77/aster-commerce-os)) — "Hermes Agent hackathon demo: commerce operator with launch packets, provider planning, and Red Tier approval gates." *Hackathon-origin; watch for follow-up; hackathon repos often don't move past submission.*
- **commerce-agent** ([BeomJuGo/commerce-agent](https://github.com/BeomJuGo/commerce-agent)) — "AI 커머스 에이전트 — 자연어 기반 상품 추천·비교·리뷰분석·고객응대·니즈 대시보드·소싱·큐레이션 (Next.js + 네이버쇼핑 + OpenAI, Vercel)" *Korean Naver Shopping + OpenAI agent. New regional variant (Korea).*
- **kapruka-agent** ([Yasiru-Silva/kapruka-agent](https://github.com/Yasiru-Silva/kapruka-agent)) — "AI shopping assistant for Kapruka.com" *Sri Lanka Kapruka.com vertical integration. Regional commerce-agent cohort is growing (Korea + Sri Lanka today).*
- **ai-agent-erp-to-shopify** ([Diego-Rave/ai-agent-erp-to-shopify](https://github.com/Diego-Rave/ai-agent-erp-to-shopify)) — "Orquestador ETL basado en agentes de IA. Extrae datos de un ERP vía FastAPI, los enriquece con Llama 3 (Groq) para SEO..." *Spanish-language merchant-side agent: ERP → Shopify ETL with LLM enrichment. Merchant-side, not consumer-side.*
- **ai201-project2-fitfindr-starter** ([manyapn/ai201-project2-fitfindr-starter](https://github.com/manyapn/ai201-project2-fitfindr-starter)) — "Multi-tool AI agent for secondhand shopping" *Vertical (secondhand) consumer-side.*
- **AI-POWERED-SMART-BUDGET-SHOPPING-SYSTEM** ([rashmijain091217-bit/AI-POWERED-SMART-BUDGET-SHOPPING-SYSTEM](https://github.com/rashmijain091217-bit/AI-POWERED-SMART-BUDGET-SHOPPING-SYSTEM)) — "AI-Powered Smart Budget Shopping System is a web application that uses AI to help users find products within their budget." *Consumer-side price-discovery with budget constraint.*
- **resonate-agentic** ([akoita/resonate-agentic](https://github.com/akoita/resonate-agentic)) — "The agentic audio protocol — AI-native music discovery, commerce & creation on Google ADK 2.0." *Agentic protocol for audio/music, not commerce. Watch only as protocol-design signal.*
- **E-Commerce-Search-Agent** ([pashajamal/E-Commerce-Search-Agent](https://github.com/pashajamal/E-Commerce-Search-Agent)) — "This is a simple web app where you type in what you're looking for (like 'best budget gaming laptop') and pick which store[s]..." *Tutorial-grade search-agent.*
- **ai-shopping-assistant / AI-shopping-agent / ai-shopping-assistant-simulator / opura-ai-shopping-assistant (×2)** — 5 distinct repos from 5 distinct authors all named "*ai-shopping-assistant*". **This is now a naming pattern at scale** — confirming the "every CS student is shipping an AI shopping assistant" trend. None have traction (all 0★). Read as ecosystem activity, not competitive threat.

**Reed pattern read:** the **n8n + shopping API cohort is the new actionable cohort this week.** Three repos (n8n-nodes-google-shopping-api, n8n-nodes-yahoo-shopping-api, AI-Shopping-Assistant-n8n-Gemini-Groq-Python) — all created within the last 7 days — are the **first independent third-party signal that n8n + price-comparison API is a viable distribution channel** for an AI shopping assistant. This is the **strongest evidence yet** that the pending n8n BuyWhere node work has a real developer-demand foundation.

**Other read:** the **"agent-readiness / AEO scoring" cohort** (agent-readiness-mcp + aso-score-mcp by forgemeshlabs + agentic-commerce-kit by nick-liyao) is the second new cohort today — three authors in 24h building tooling around "score your website for AI agent fitness." Reed recommendation: **add "agent-readiness scoring (AEO for agents)" to the weekly tier list as a peer-watch item.** Within Reed's authority — tier-list update only.

## Medium-Tier GitHub (selected, 12 total)

- **local-browser-mcp** ([NolanLT/local-browser-mcp](https://github.com/NolanLT/local-browser-mcp)) — **5★** (▲ from 1★ yesterday? — *first entry into today's dataset*), "Headless, agent-controllable real browser as an MCP server — drive local dev servers from Claude." *Highest-traction MCP server in today's digest. Not commerce directly, but the agent-controllable-browser capability is the **substrate that could enable a BuyWhere agent to drive any merchant site without a merchant-side adapter** — bookmark for the next Reed product strategy review as a "watch this" technology primitive.*
- **chakravyuh-ai** ([krushna081/chakravyuh-ai](https://github.com/krushna081/chakravyuh-ai)) — 2★, "An open-source multi-agent AI operating system connecting AI models, agents, MCP servers, and autonomous workflows." *Multi-agent OS framing, not commerce.*
- **pcx-ai-toolkit** ([VoidChecksum/pcx-ai-toolkit](https://github.com/VoidChecksum/pcx-ai-toolkit)) — 3★, "AI-powered scripting toolkit for Perception.cx." *Game scripting toolkit, not commerce.*
- **linkedin-mcp** ([joaovaleri/linkedin-mcp](https://github.com/joaovaleri/linkedin-mcp)) — 2★, "MCP server for editing your own LinkedIn profile via Playwright browser automation." *Not commerce.*
- **danbooru-MCP** ([echo-xianyu/danbooru-MCP](https://github.com/echo-xianyu/danbooru-MCP)) — 2★, "MCP server for searching Danbooru characters and related tags." *Not commerce.*
- **js-reverse-pro-mcp** ([a0yark/js-reverse-pro-mcp](https://github.com/a0yark/js-reverse-pro-mcp)) — 2★, "JS reverse engineering MCP server (Pro fork)." *Not commerce.*
- **mcp / mcp-server-dotnet / mcp-doc-server / firmware-mcp-server** — 1★ each, generic MCP server scaffolding. Not commerce.

**Read:** medium-tier continues to be **mostly MCP server noise with no commerce relevance.** No change from yesterday. The 5★ local-browser-mcp entry is the standout.

## Agentic-Commerce / x402 Mentions (HN)

- **None at high-tier today.** The two HN medium-tier keyword matches are Spanly (MCP analytics, not agentic commerce) and centri (generic stateful-agent). The Visa+OpenAI story is out of the 7-day window for the first time in 9 days.
- **x402 cohort (GitHub, agentic-commerce + x402):** agent-commerce (Kubudak90, Arcorapay merchant via x402), plus carried-over x402 repos from prior briefs. No new high-traffic x402+commerce GitHub repos today beyond what was reported in the 06-15/16 briefs.

## Monitor / No-Action Items

- Launch HN: Adam (YC W25) 149pt — "Buy for Me" substring false positive (AI CAD, not commerce).
- Show HN: Veterinarian turned founder, AI lawn diagnosis 75pt — "Amazon Buy for Me" substring false positive (AI lawn care).
- Show HN: VoiceDraw 47pt, Show HN: Sabela (Haskell) 44pt, Ask HN: job hunting 12pt, Show HN: 3 coding agents non-stop 10pt — all "Buy for Me" substring false positives.
- Show HN: Memento 9pt, Show HN: ML condenses logs 8pt, Show HN: Write GitHub Actions in TypeScript 7pt, Ask HN: metric for AI code quality 6pt — substring false positives.
- Show HN: Agentspace 5pt — YOLO agent sessions, not commerce.
- Ford's New $30k Electric Truck 4pt — "Universal Cart" substring false positive (car model).
- Most of CVE-2026-4020 attackers 6pt — x402 substring false positive (CVE, not payments).
- Struggling for My Startup 2pt, Show HN: BlitzGraph 2pt, Show HN: Thulr 3pt, Show HN: spelling app 2pt, Show HN: Musefs 2pt, Show HN: Chess bot 2pt, Show HN: ELDC 3pt, Ask HN: Apple Silicon 2pt, Ask HN: data warehouse 4pt, Safety Ideas 2pt, Ask HN: data warehouse 4pt — all substring false positives, ignore for product strategy.

## Source Data

- Raw JSON: `data/competitor_intelligence_2026-06-18.json` (72 entries, 2 platform errors)
- Script: `scripts/competitor_intelligence.py` (HN: 7-day window, 11 keywords; GitHub: 1-day window, 4 keywords)
- HN window: `created_at_i > now-7d`; GitHub window: `created:>YYYY-MM-DD` (UTC)
- Deduplication: HN by `objectID`; GitHub by `html_url`

## Strategic Recommendations (for the daily brief to Vera)

1. **Visa+OpenAI story has aged out of HN 7-day window — reclassify.** First time in 9 days the AP News + WSJ submissions are no longer in the HN Algolia 7-day window. **Reed recommendation: reclassify "Visa plugs payment network into ChatGPT" from active strategic watch to background context** in the weekly tier list. No replacement top-of-mind HN story surfaced today. Within Reed's authority — tier-list update only.
2. **n8n + shopping API cohort is now a real signal — promote the BuyWhere n8n node child.** Three independent third-party repos (n8n-nodes-google-shopping-api, n8n-nodes-yahoo-shopping-api by johnisanerd; AI-Shopping-Assistant-n8n-Gemini-Groq-Python by TAMBESANTOSH077) confirm developer demand. **Reed recommendation: file a dedicated child issue for the n8n BuyWhere node this week** (carried from 2026-06-13/14/15/16 briefs — promote from "fold-in to next weekly brief" to "file this week"). Implementation routes to Rex or Bolt; Reed files the child.
3. **"agent-readiness scoring (AEO for agents)" is a new cohort — add to weekly tier list.** agent-readiness-mcp + aso-score-mcp (forgemeshlabs) + agentic-commerce-kit (nick-liyao) — three authors in 24h building tooling around "score your website for AI agent fitness." Reed recommendation: add as peer-watch item. Within Reed's authority — tier-list update only.
4. **local-browser-mcp (5★) is the substrate that could enable a BuyWhere agent to drive any merchant site without a merchant-side adapter.** Worth a deeper look at the next Reed product strategy review. No immediate action — purely a technology-primitive watch item.
5. **n8n BuyWhere node child filing — formalize scope.** (Carried from 2026-06-13/14/15/16 briefs.) Reed will draft and file this child this week, blocker-set to nil (no external dependency), assignee set to Rex with Bolt fallback. **No new issue needed today; will file as part of this digest's commit sequence.**
6. **Onchain-agent commerce cohort (multi-chain) is now 5+ repos in 7 days.** (agent-commerce-kit, pfn-hedera-commerce-agent, CorrFarm-x402-agentic-commerce, pfn-guarded-commerce-agent, agent-commerce today.) x402 + multi-chain is the de facto payment-rail default. Reed recommendation: keep "onchain-agent commerce (multi-chain)" on the weekly tier list. No change.
7. **"agentic-commerce-*" naming cohort still leading indicator.** Today's hits: agentic-commerce-kit + webaz + ace (carried) + agent-commerce (Arcorapay) + agent-commerce-hub-cobo-hackathon (carried). 5+ repos in 7 days with the agentic-commerce-* / agent-commerce-* naming pattern. No change to weekly tier list.
8. **ChatGPT Shopping trust/safety pressure (Guardian + AP coverage).** No fresh HN story today; the underlying narrative is the same. Marketing one-pager citation (Reed-approved copy) remains recommended.

## Recommended Actions (operational, within Reed's authority)

1. **File n8n BuyWhere node child issue this week** — promote from "pending fold-in" to "file this week." Reed files the child in the next routine fire; implementation routes to Rex/Bolt. (Promoted from 2026-06-13/14/15/16 briefs.)
2. **Add "agent-readiness scoring (AEO for agents)" to the weekly tier list** — peer-watch item. Tier-list update only; no new issue needed. (NEW today.)
3. **Reclassify "Visa plugs payment network into ChatGPT" from active strategic watch to background context** — no longer in HN 7-day window. Tier-list update only; no new issue needed. (NEW today.)
4. **Inspect local-browser-mcp (5★) for cross-reference at next Reed product strategy review** — technology-primitive watch. No new issue needed. (NEW today.)
5. **Add "agent-commerce (Arcorapay merchant via x402)" to onchain-agent commerce cohort** — already in cohort; no new issue needed.
6. **Tighten GitHub keyword set** — drop "mcp server" from `scripts/competitor_intelligence.py` and replace with a commerce-anchored variant (e.g. "shopping mcp server" / "checkout mcp"). Reed will apply in the next routine fire. **No new issue needed; in-script tweak only.** (Carried from 2026-06-13/14/15/16 briefs.)
7. **Re-attempt Smithery endpoint** — current URL `https://smithery.ai/api/mcp` returns 404. Try `https://smithery.ai/api/servers` or check their public docs for a new endpoint; restore that source to the daily digest. (Carried from 2026-06-13/14/15/16 briefs.)

## Unresolved / Not Actionable This Heartbeat

- PH_API_TOKEN is not in this workspace's env. Surf (the Product Hunt monitoring agent per the parent spec) owns that token request; flagged in [BUY-30944 docs](/BUY/issues/BUY-30944) since 2026-06-05.
- Reddit/Discord monitoring is still gated on [BUY-8722](/BUY/issues/BUY-8722) resolution. No Reddit/Discord data in this digest.

## Related

- Parent: [BUY-7445](/BUY/issues/BUY-7445) (Daily community monitoring for competitor intelligence pipeline)
- Spec root: [BUY-7443](/BUY/issues/BUY-7443) (Set up competitor intelligence monitoring workflow)
- Reed mandate: [BUY-7435](/BUY/issues/BUY-7435) (Reed — Chief Product Officer: Expanded Mandate & Execution Plan)
- Prior digest (06-16): `docs/buy-52145-daily-competitor-intel-2026-06-16.md` (referenced in commit `2fc8003`)
- Prior digest (06-15): `docs/buy-50370-daily-competitor-intel-2026-06-15.md` (referenced in commit `abc5767`)
- Prior digest (06-14): `docs/buy-47606-daily-competitor-intel-2026-06-14.md` (referenced in commit `d6c0e9f`)
- Prior digest (06-13): `docs/buy-45123-daily-competitor-intel-2026-06-13.md` (referenced in commit `476dc0a`)
- AI Agent Leads cohort: `docs/buy-8032-ai-agent-leads-2026-05-29.md`
