# Opportunity OS Outcomes + Self-Optimization + Cutover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure real business outcomes, learn from Jonas's ratings without corrupting objective scoring, tune research allocation, and safely cut user-facing output over from AI Radar to Opportunity OS.

**Architecture:** Workflow 58 turns each successful build into scheduled measurement tasks and records actual outcomes. Workflow 59 learns two bounded things separately: Jonas Fit from 1–10 ratings and research/source allocation from actual outcomes. Cutover happens only after a shadow period proves the new publisher is more useful and does not lose current Radar coverage.

**Tech Stack:** n8n, n8n Data Tables, existing Clarity/Notion/order data where available, OpenRouter for bounded summarization, Discord.

**Spec:** `docs/superpowers/specs/2026-09-19-opportunity-os-design.md`

## Global Constraints

- Jonas Fit may reorder/tie-break what Jonas sees but may not change objective Business Value.
- Self-Optimizer may change bounded research weights, never activate/retire a strategic goal by itself.
- Source weights remain between 0.25 and 2.0.
- Hunt research weights remain between 10 and 100.
- Existing Radar workflows are disabled only after explicit shadow-run acceptance criteria pass.
- Historical AI Radar tables are retained.
- No automatic deletion of outcome/history rows.
- Cost of the Opportunity OS itself must be measured.

## Review Focus

1. Missing outcome data must remain UNKNOWN, not be treated as zero benefit.
2. A single 10/10 rating must not dominate Jonas Fit.
3. A source with low short-term ratings but strong measured outcomes must not be suppressed into silence.
4. Optimization weights must never drift outside hard bounds.
5. Cutover must not disable current user-facing Radar before OS buttons and publishing are verified in production.

---

### Task 1: Create `GK_OS_OUTCOMES` and OS config

**Objects:**
- Create Data Table: `GK_OS_OUTCOMES`
- Create Data Table: `GK_OS_CONFIG`

**Interfaces:**
- Produces: durable measurement rows and bounded optimizer configuration.

- [ ] **Step 1: Create `GK_OS_OUTCOMES`**

```json
[
  {"name":"outcome_id","type":"string"},
  {"name":"opportunity_id","type":"string"},
  {"name":"job_id","type":"string"},
  {"name":"metric_name","type":"string"},
  {"name":"baseline_value","type":"number"},
  {"name":"expected_value","type":"number"},
  {"name":"measured_value","type":"number"},
  {"name":"unit","type":"string"},
  {"name":"source_ref","type":"string"},
  {"name":"measurement_window_days","type":"number"},
  {"name":"status","type":"string"},
  {"name":"due_at","type":"date"},
  {"name":"measured_at","type":"date"},
  {"name":"notes","type":"string"},
  {"name":"created_at","type":"date"},
  {"name":"updated_at","type":"date"}
]
```

- [ ] **Step 2: Create `GK_OS_CONFIG`**

```json
[
  {"name":"config_key","type":"string"},
  {"name":"config_value","type":"string"},
  {"name":"config_number","type":"number"},
  {"name":"config_bool","type":"boolean"},
  {"name":"updated_at","type":"date"},
  {"name":"notes","type":"string"}
]
```

- [ ] **Step 3: Seed bounded defaults**

```json
[
  {"config_key":"daily_publish_cap","config_number":3,"config_bool":true},
  {"config_key":"source_weight_min","config_number":0.25,"config_bool":true},
  {"config_key":"source_weight_max","config_number":2.0,"config_bool":true},
  {"config_key":"hunt_weight_min","config_number":10,"config_bool":true},
  {"config_key":"hunt_weight_max","config_number":100,"config_bool":true},
  {"config_key":"jonas_fit_min_samples","config_number":5,"config_bool":true},
  {"config_key":"autonomous_monthly_spend_sek","config_number":0,"config_bool":true}
]
```

### Task 2: Build `58 OS – Outcome Tracker`

**Objects:**
- Create n8n workflow: `58 OS – Outcome Tracker`

**Interfaces:**
- Consumes: SUCCEEDED build jobs + opportunity `metric_plan_json`.
- Produces: DUE/MEASURED/UNKNOWN outcome rows.

- [ ] **Step 1: Create inactive workflow with Manual Trigger and daily Schedule Trigger 07:00 Europe/Stockholm**

Use standard OS settings; timeout 120s.

- [ ] **Step 2: Materialize outcome rows when a build succeeds**

For each metric plan entry create:

```js
outcome_id = "OUT-" + sha256(job_id + ":" + metric_name + ":" + measurement_window_days).slice(0,12)
```

Set:
- `status="DUE"`
- `due_at = finished_at + measurement_window_days`.

Upsert by `outcome_id`.

- [ ] **Step 3: Map supported metric sources**

Initial supported source families:

```text
GK_ORDERS          -> order count, revenue-like amount aggregates, repurchase indicators where directly derivable
Clarity summary    -> page-level friction/CRO metrics when connector/source data is available
n8n workflow data  -> execution/error counts only when safely measurable
manual_time        -> UNKNOWN until a measured baseline/result exists
external_revenue   -> UNKNOWN unless a verified data source is attached
```

Never infer a missing metric.

- [ ] **Step 4: Capture baseline before/at deployment when possible**

If the metric plan has a measurable source, record baseline before the deployment timestamp or from the stored baseline reference.

If unavailable:
- keep `baseline_value` null,
- set notes `Baseline unavailable; outcome cannot be expressed as a reliable delta.`.

- [ ] **Step 5: Measure due outcomes**

For rows with `status="DUE"` and `due_at <= now`:
- fetch the specified source,
- calculate metric,
- store `measured_value`,
- set `status="MEASURED"`.

If source is inaccessible:
- `status="UNKNOWN"`,
- preserve the reason.

- [ ] **Step 6: Calculate outcome direction, not fake ROI**

Store notes with:
- improved / unchanged / worsened,
- delta when baseline exists,
- whether expectation was met.

Do not invent SEK value for time saved unless a verified monetary conversion rule exists.

- [ ] **Step 7: Test missing source**

Expected: UNKNOWN, not zero.

- [ ] **Step 8: Test measurable source**

Pin baseline 10 and measured 7 for a lower-is-better metric.

Expected: MEASURED with improvement of 3 units and correct direction.

- [ ] **Step 9: Publish workflow after tests pass**

### Task 3: Build Jonas Fit learner inside `59 OS – Self Optimizer`

**Objects:**
- Create n8n workflow: `59 OS – Self Optimizer`
- Reads: `GK_OS_FEEDBACK`, `GK_OS_OPPORTUNITIES`, `GK_OS_OUTCOMES`, `GK_OS_HUNTS`, source context/config.

**Interfaces:**
- Produces: `jonas_fit` updates and bounded research/source weights.

- [ ] **Step 1: Create inactive workflow with Manual Trigger and weekly Schedule Trigger Sunday 22:30 Europe/Stockholm**

Use standard OS settings; timeout 180s.

- [ ] **Step 2: Join ratings to opportunities by entity ID**

Never use positional joins.

Extract dimensions:

```text
origin:<origin_type>
goal:<goal_id>
cost:free_or_zero | paid_known | unknown
effort:quick | medium | heavy
target:<target_type>
theme:new_revenue | cro | automation | product | partner | support | data | content | other
```

- [ ] **Step 3: Require minimum sample size**

Do not change `jonas_fit` from neutral 50 until at least 5 Jonas opportunity ratings exist.

For a dimension-specific effect require at least 2 ratings in that dimension.

- [ ] **Step 4: Apply light recency weights**

```text
<=30 days: 1.25
31–90 days: 1.00
>90 days: 0.75
```

- [ ] **Step 5: Convert preference average to bounded fit**

For matching stable dimensions:
- average 5.5 -> no effect,
- bounded total modifier -15 to +15,
- final `jonas_fit` range 0–100,
- base = 50.

Do not write to `business_value`, evidence, cost, confidence, or goal state.

- [ ] **Step 6: Test five-rating boundary**

Four ratings -> fit remains 50.

Fifth valid rating -> learner may update fit.

### Task 4: Add outcome-aware source/hunt optimizer

**Objects:**
- Modify workflow: `59 OS – Self Optimizer`
- Modify rows: `GK_OS_HUNTS`, `GK_OS_CONFIG`

**Interfaces:**
- Produces: bounded `research_weight` changes and source-weight config.

- [ ] **Step 1: Calculate source quality from two signals**

Per source/origin over rolling 90 days:

```text
attention_quality = mean Jonas rating, only when sample size >= 3
outcome_quality = share of MEASURED builds that met expected direction, only when sample size >= 2
```

When one signal lacks enough data, use the other; when both lack data, keep current weight.

- [ ] **Step 2: Change weights slowly**

Maximum weekly change:
- source weight: ±0.15
- hunt research weight: ±10 points.

Hard bounds:
- source 0.25–2.0
- hunt 10–100.

- [ ] **Step 3: Protect high-outcome/low-rating sources**

If outcome_quality is strong but ratings are low, do not reduce source weight below 0.75.

This prevents personal taste from suppressing objectively valuable evidence.

- [ ] **Step 4: Increase neglected-goal research**

If an ACTIVE strategic goal has:
- no READY_TO_PUBLISH/PUBLISHED opportunity in 30 days, and
- fewer than 3 researched candidates,

increase its active hunt weights by +10, capped at 100.

- [ ] **Step 5: Never activate/retire strategic goals**

59 may write a recommendation into `GK_OS_CONTEXT` with key `optimizer:goal:<goal_id>`, but goal status changes remain Jonas-only.

### Task 5: Add Opportunity OS system KPIs

**Objects:**
- Modify workflow: `59 OS – Self Optimizer`
- Write config row: `os_weekly_kpi_summary`

**Interfaces:**
- Produces a compact weekly machine-readable summary.

- [ ] **Step 1: Calculate weekly KPIs**

```text
generated_candidates
researched_candidates
published_opportunities
rated_opportunities
rating_8_to_10_share
rating_1_to_4_share
build_actions
successful_builds
rolled_back_builds
measured_positive_outcomes
unknown_outcomes
estimated_ai_cost_sek_when_available
posts_per_active_goal
```

- [ ] **Step 2: Store KPI JSON in `GK_OS_CONFIG`**

Key: `os_weekly_kpi_summary`.

No Discord post is required unless there is a material warning or the user later asks for a weekly digest.

- [ ] **Step 3: Add self-health warnings**

Create a user-facing warning candidate only when:
- >50% of published opportunities receive ratings 1–4 over >=10 ratings,
- worker rollback/failure rate >25% over >=4 build jobs,
- one source produces >50% of all published posts over 30 days,
- daily publish cap is repeatedly saturated for 5+ days.

Warnings are plain Swedish and treated as internal OS health, not AI news.

### Task 6: Run shadow comparison before cutover

**Objects:**
- Existing: workflows 30–37
- New: workflows 50–59

**Interfaces:**
- AI Radar remains live.
- Opportunity OS Publisher runs in shadow mode first: formats/stores would-be posts without Discord POST.

- [ ] **Step 1: Add `publisher_shadow_mode=true` in `GK_OS_CONFIG`**

55 must skip Discord POST while still persisting a preview record/context entry.

- [ ] **Step 2: Run shadow mode for at least five complete Opportunity OS cycles**

A complete cycle means:
- generator ran,
- enricher processed candidates,
- judge finalized decisions,
- publisher evaluated queue.

- [ ] **Step 3: Compare against AI Radar output**

Check:
- would OS have repeated low-value Radar noise?
- did OS preserve genuinely useful Radar findings?
- are OS explanations understandable without technical context?
- is post volume lower/equal while decision quality is higher?

- [ ] **Step 4: Verify button paths in production separately**

Use one controlled OS QA post before general cutover.

Expected: rating, BYGG, INTE NU, MER INFO, Jonas authorization all work.

### Task 7: Cut user-facing output over safely

**Objects:**
- Modify workflow: `55 OS – Opportunity Publisher`
- Disable direct publishing workflow only: `32 AI – Radar Publisher` (`NPttHcn1wkAzBkx2`)
- Keep collection/analysis history: 30, 31, 31B, 34, 35 as needed during transition.

- [ ] **Step 1: Turn shadow mode off**

Set `publisher_shadow_mode=false`.

- [ ] **Step 2: Publish one real OS opportunity**

Verify Discord content + buttons + stored message ID.

- [ ] **Step 3: Disable only direct AI Radar user-facing publishing**

Unpublish/disable workflow 32 after OS production post succeeds.

Do not delete it.

- [ ] **Step 4: Keep Radar as input layer**

30/31/31B/34 continue producing external AI signals for the Opportunity Engine unless later evidence shows a specific stage is redundant.

- [ ] **Step 5: Keep old signed interaction routes during transition**

37 continues supporting old message buttons already in Discord so historical posts do not break.

### Task 8: Final acceptance test

- [ ] **Step 1: Goal proposal**

Expected: AI can propose a strategic goal; only Jonas action can activate it.

- [ ] **Step 2: Goal-driven idea**

Expected: ACTIVE goal creates hunts and produces at least one researched candidate.

- [ ] **Step 3: External AI signal**

Expected: a new Radar signal is evaluated against goals/context rather than posted raw.

- [ ] **Step 4: Plain-language Discord**

Expected: Nicholas can understand the card without system background; no technical score leakage.

- [ ] **Step 5: Rating**

Expected: Jonas 1–10 stored in GK_OS_FEEDBACK; Business Value remains unchanged.

- [ ] **Step 6: BYGG**

Expected: one durable build job; policy gates apply; supported adapter executes through verification.

- [ ] **Step 7: Shopify MAIN**

Expected: experiment-site may be built/tested; MAIN requires separate Jonas approval.

- [ ] **Step 8: Outcome**

Expected: at least one build creates a due outcome and later becomes MEASURED or explicitly UNKNOWN.

- [ ] **Step 9: Self-optimization**

Expected: weekly learner changes only bounded preference/research weights and cannot activate goals.

- [ ] **Step 10: Historical preservation**

Expected: old AI Radar data/workflows remain recoverable; no historical tables are deleted.
