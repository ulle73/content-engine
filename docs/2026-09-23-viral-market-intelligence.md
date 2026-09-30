# Viral & Market Intelligence

Implementation on `codex/viral-market-intelligence`, based on `origin/main` at
`780468c` (closed-loop generation learning). Local `main` was not changed.

## Architecture

Virlo discovers the broader market; Apify retains explicit tracked-account and
tracked-advertiser collection. No new queue, scheduler or learning model.

`market_intelligence` is a stage in `run_daily`. Active owners' companies with a
profile and `market_intelligence_enabled=True` use one-shot Virlo agents in three
stable weekly windows: Monday–Tuesday, Wednesday–Thursday, Friday–Sunday. Delayed
runs can catch the current window; no catch-up burst. Pause is company-specific.
Missing credentials cause a visible skipped stage without a paid reservation.

Each research agent uses `platforms=["instagram"]`, `meta_ads_enabled=true`,
`is_recurring=false`, `english_only=false`, and `data_intelligence_enabled=false`.
Free keyword suggestions derive niche queries from the selected company's name
and profile. The config is cached against profile/current/voice. Profile changes
invalidate old eligibility and analysis; an in-flight old-scope run cannot become
new-scope guidance. Fresh research is admitted in the next cadence window.

One-shot agents keep billing under our scheduler's control and prevent provider
recurrence or autonomy settings from creating an additional billing schedule.
No TikTok or YouTube requests or eligible items are allowed.

### Current provider contracts checked on 2026-09-23

- [Virlo Agents](https://dev.virlo.ai/docs/agents): `/v1/agents/suggest-keywords`,
  `POST /v1/agents`, `GET /v1/agents/{id}`, `/videos`, `/creators/outliers`, `/ads`.
- [Virlo OpenAPI](https://api.virlo.ai/openapi.json): verified actual DTOs and
  parameters, including `platforms` for videos versus `platform` for outliers,
  `ad_archive_id`, `partial_failure`, and nested `data` collections. Ads' `url`
  can be a landing page: canonical identity comes from `ad_archive_id` first.
- [Virlo billing](https://dev.virlo.ai/docs/credits): response `X-Cost`, free reads,
  $0.50 base agent run, optional +$1.00 data-intelligence add-on (disabled here).
- [Apify Actor runs](https://docs.apify.com/api/v2/actors-runs-post) and
  [dataset items](https://docs.apify.com/api/v2/dataset-items-get): existing
  asynchronous Actor run, status, dataset, and provider charge-cap flow retained.

Orbit and Comet are deprecated; no legacy endpoints are introduced.

## Qualification and creative analysis

Read at most 50 recent videos, 50 ranked creator outliers with at most ten video
examples each, and 50 ads per run. This is a bounded sample, not exhaustive market
coverage. The video read is limited to the last 30 days; missing or future dates
cannot qualify an organic item.

Cheap checks run before our AI analysis:

1. Allowlisted original URLs, channel, canonical identity and recency.
2. Company/profile or generated niche-keyword overlap, provider intent rejection
   when available, and company-specific relevance-feedback similarity.
3. For organic content, either at least 2x creator corpus median with at least
   five baseline posts, or weighted follower-reach score >=18 using Virlo's
   documented `ln(views/followers) * ln(followers)` approach.

Absolute views, views/followers and creator-relative performance remain separate
metrics. The corpus median is explicitly labelled; it is not an age-matched,
whole-account historical baseline. Views/followers is never called a measured
improvement over that creator's usual performance. Missing metrics remain null.
Ads are market observations, never measured CTR/CPA/ROAS or proven winners.
Only active-state and observed dates are retained as ad visibility metadata.

At most two organic and two paid candidates are analyzed per invocation, within
the existing shared `INTELLIGENCE_DAILY_ANALYSES` limit (default 12/company/day).
Cached analysis uses `AnalysisMemo` and existing OpenRouter routing and usage
tracking. Unknown market analyses do not use automatic stale-memo retries.
Failed analysis does not erase previously collected evidence.

Analysis abstracts hook, format, mechanisms, story, offer, CTA, emotional angle
and an original company adaptation. This implementation analyzes captions and
metadata, not video/audio: visual opening and pacing must remain unknown without
supporting evidence. It deliberately avoids transcript downloads and the broad
per-video paid enrichment add-on. Two or more qualified examples across multiple
creators can surface recurring mechanism hypotheses; these are not causal claims
or measured trend acceleration.

## Isolation, deduplication and paid-call safety

- Every item belongs to a company; canonical uniqueness is `(company, key)`.
- Instagram shortcode and Meta archive id deduplicate within a company.
- Each Virlo observation links to its existing `ScrapeRequest`, provider id,
  observed metrics and timestamp. Apify matches are resolved within the same
  company, including Apify content imported later. Generation removes duplicate
  originals while preserving Virlo and Apify provenance.
- Existing company/state transaction locks reserve calls before provider POST.
  A stable cadence-period key prevents another reservation across the same window.
- Unknown/missing start responses block another paid start, including future
  windows. A known remote id can be polled safely. Unknown remote states never
  count as completed; reads can resume without creating a new agent.
- Completed reads are idempotent. Partial provider failures retain usable items
  and surface attention in the daily ledger.
- UI, feedback, ideas, MCP and Creative Engine all validate company ownership.
  Feedback and external observations never write `OwnOutcome` or training labels.

`reconcile_market` attaches an operator-verified remote agent to a reserved unknown
start. It validates the company, nonrecurring Instagram/Meta config, intent and
keywords before linking; it only performs a free provider GET:

```text
python manage.py reconcile_market --company COMPANY_UUID --request REQUEST_ID --agent AGENT_UUID
```

Optional `--reported-cost-usd` is for an actual amount verified in provider billing,
never an estimate. If no accepted remote agent can be found, investigate Virlo
billing/support before changing the reservation; do not clear unknown starts just
to retry. Errors and credentials are not persisted as raw response bodies.

## Learning and generation

`generation_guidance` is the authoritative existing closed-loop implementation,
now with time cutoffs. `generation_learning_profile` is a compatibility view of
its own-performance section; its second aggregation algorithm was removed.
Legacy snapshot keys remain readable but duplicated profiles are excluded from
model payloads when canonical guidance exists.

`attach_generation_evidence` supplies both web and MCP generation with four
separate sections, frozen in the run:

| Section | Meaning |
| --- | --- |
| `performance` | Verified own outcomes; strongest performance guidance |
| `external_viral_performance` | Qualified external Instagram observations |
| `market_evidence` | Competitor observations and external Meta creatives |
| `editorial` | Choices, edits, rejections and market relevance preferences |

The own-result training dataset, chronological evaluation and promotion gates
remain intact. Editorial similarity affects eligibility, never performance score
or outcome labels. External examples receive no fabricated predicted-score boost.
The instruction hierarchy gives own measured outcomes priority; company profile
and current facts remain the only factual source for new claims.

Both idea and final-copy requests receive the evidence. Selecting a market item
also opens Creative Engine with its original adaptation. Its frozen abstract
mechanisms enter the existing media prompt compiler with source ids; original
captions and external metrics are not copied into media prompts.

Generic guidance, UI labels and help examples no longer assume Golfkuponger.

## UI and cost

Inspiration → Marknaden provides Instagram/Meta tabs, originals, metrics, reasons,
company adaptation, mechanisms, cross-provider provenance, patterns, discovery
status, reported costs, pause/resume, Relevant/Inte relevant, undo, idea generation,
and handoff to Creative Engine. It uses the existing design system.

Default research price: **$0.50/run**, **$1.50/week/company**, approximately
**$6.50/average month/company**, plus existing metered text analysis. No new paid
calls were made during implementation. Runtime actual cost comes from `X-Cost`;
missing reports remain unknown and are not shown as a measured zero. Virlo has
separate totals/rows in the existing cost screen. Unknown requests reserve $0.50
against the shared `SCRAPER_DAILY_BUDGET_USD` (default $1/company/day).

The reservation is an application estimate, not a Virlo-enforced price cap;
provider price changes require updating the estimate. Apify's existing provider
charge cap is unchanged. Existing competitor work runs first and can consume the
shared daily budget, deferring research; raise the configured budget only when
that trade-off is intended.

## Verification and remaining external steps

- New fixture tests cover current request/response contracts, organic/ad discovery,
  qualified-only AI, relative versus absolute metrics, company/owner isolation,
  content and paid-call dedupe, shared budget, unknown/partial states, retries,
  provenance, feedback and undo, scope changes, costs, web/MCP generation,
  actual generation payload and Creative Engine prompt handoff, and reconciliation.
- 94 targeted tests passed (learning, intelligence/Apify, costs, daily scheduler,
  Creative Engine and operator bridge). PostgreSQL concurrency coverage was added;
  running it requires an isolated `TEST_DATABASE_URL`.
- Final full suite: 247 discovered; 242 passed, 3 PostgreSQL-only skips, 2 existing
  failures. The remaining failures also reproduce on unmodified `origin/main`:
  `test_stale_openrouter_started_memo_recovers_after_worker_restart` constructs
  a MagicMock instead of a datetime; `test_ai_studio_exposes_priority_format_and_safe_diagnostics`
  expects the old media-panel text order. No change was made to those unrelated tests.
- `manage.py check` and `makemigrations --check --dry-run` pass against isolated
  test settings. Migration 0014 was exercised only in local test databases.
- Headless Edge/Playwright on local fixture data: 1440px desktop and 390px mobile,
  organic/paid views, no horizontal overflow. Screenshots in ignored local
  `data/market-desktop.png`, `data/market-mobile.png`, `data/market-paid-mobile.png`.

**Not live-verified:** local `VIRLO_API_KEY`, `OPENROUTER_API_KEY` and an isolated
PostgreSQL test URL are absent. The implementation has not been deployed or pushed.

To activate externally: deploy this branch, apply migration 0014, configure
`VIRLO_API_KEY` and the existing OpenRouter credentials in the server secret store,
and ensure existing `run_daily` continues running. Use the UI research control or:

```text
python manage.py run_daily --company COMPANY_UUID --wait-seconds 720
```

Verify one live company's Instagram and Meta response, original links, reported
cost and generated idea. Then verify a second company stays isolated. Provider
schema fixtures are verified against public documentation, but cannot substitute
for that credentialed smoke test. PostgreSQL concurrency tests must use a dedicated
test database with `--settings=engine.postgres_test_settings`, never production.
