# Opportunity OS Generation + Evidence + Judgment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn active goals, Golfkuponger context, real frictions, and external AI signals into a small queue of deduplicated, researched, skeptical, decision-grade opportunities.

**Architecture:** Workflow 52 generates candidates but is not allowed to approve them. Workflow 53 enriches only the strongest candidates with source evidence. Workflow 54 uses separate Judge and Skeptic passes followed by a deterministic gate. This separation prevents the idea-generating model from approving its own work.

**Tech Stack:** n8n, OpenRouter `openrouter/free`, n8n Data Tables, HTTP Request nodes for direct source URLs, existing AI Radar tables.

**Spec:** `docs/superpowers/specs/2026-09-19-opportunity-os-design.md`

## Global Constraints

- Existing 30–37 AI Radar workflows remain active during this phase.
- New AI Radar signals are input material, not automatically user-facing output.
- Business Value is objective; Jonas Fit is separate.
- Low-cost/free models are used for broad generation and first-pass analysis.
- Evidence must be attributable to stored source refs; unverifiable claims cannot be upgraded to build-ready.
- No opportunity is published in this phase.
- No production changes are made.
- Shared error workflow: `64S3vgFFDl7a2yHT`.
- Timezone: `Europe/Stockholm`.

## Review Focus

1. The same external release appearing from several sources must collapse into one opportunity candidate.
2. A candidate with impressive prose but weak evidence must not become high-confidence/build-ready.
3. A source fetch failure must downgrade evidence, not fabricate supporting facts.
4. An opportunity tied to no active goal may still survive only when it has exceptional cross-company value; the reason must be explicit.
5. The Skeptic pass must be able to downgrade or dismiss a high Judge score.

---

### Task 1: Create `GK_OS_OPPORTUNITIES`

**Objects:**
- Create Data Table: `GK_OS_OPPORTUNITIES`

**Interfaces:**
- Produces: durable candidate/evidence/judgment state for workflows 52–59.

- [ ] **Step 1: Confirm the table does not exist**

Run `search_data_tables(projectId="zoZ6lq8bWNd3jueo", query="GK_OS_OPPORTUNITIES", limit=10)`.

Expected: no exact table match.

- [ ] **Step 2: Create the table with this exact schema**

```json
[
  {"name":"opportunity_id","type":"string"},
  {"name":"dedupe_key","type":"string"},
  {"name":"title","type":"string"},
  {"name":"simple_summary","type":"string"},
  {"name":"why_now","type":"string"},
  {"name":"recommendation","type":"string"},
  {"name":"goal_ids_json","type":"string"},
  {"name":"origin_types_json","type":"string"},
  {"name":"source_refs_json","type":"string"},
  {"name":"evidence_json","type":"string"},
  {"name":"asset_links_json","type":"string"},
  {"name":"risks_json","type":"string"},
  {"name":"build_plan_json","type":"string"},
  {"name":"metric_plan_json","type":"string"},
  {"name":"implementation_target","type":"string"},
  {"name":"business_value","type":"number"},
  {"name":"jonas_fit","type":"number"},
  {"name":"confidence","type":"number"},
  {"name":"effort_score","type":"number"},
  {"name":"cost_score","type":"number"},
  {"name":"reversibility_score","type":"number"},
  {"name":"evidence_grade","type":"string"},
  {"name":"skeptic_verdict","type":"string"},
  {"name":"pricing_summary","type":"string"},
  {"name":"monthly_cost_est","type":"number"},
  {"name":"setup_hours","type":"number"},
  {"name":"potential_saving","type":"number"},
  {"name":"research_status","type":"string"},
  {"name":"decision_status","type":"string"},
  {"name":"pedagogy_text","type":"string"},
  {"name":"more_info_text","type":"string"},
  {"name":"discord_message_id","type":"string"},
  {"name":"first_seen_at","type":"date"},
  {"name":"last_seen_at","type":"date"},
  {"name":"recheck_after","type":"date"},
  {"name":"published_at","type":"date"},
  {"name":"updated_at","type":"date"}
]
```

- [ ] **Step 3: Verify the schema**

Expected: every name/type matches exactly.

### Task 2: Build `52 OS – Opportunity Generator`

**Objects:**
- Create n8n workflow: `52 OS – Opportunity Generator`
- Folder: `30 AI RADAR` (`NXv5tH5JyNYNUY9t`)

**Interfaces:**
- Consumes:
  - ACTIVE company/strategic goals from `GK_OS_GOALS`
  - ACTIVE hunts from `GK_OS_HUNTS`
  - CURRENT context from `GK_OS_CONTEXT`
  - recent relevant rows from `GK_AI_RADAR_ITEMS`
  - existing `GK_OS_OPPORTUNITIES` for dedupe/history
- Produces: `research_status="RESEARCH_PENDING"` candidates in `GK_OS_OPPORTUNITIES`.

- [ ] **Step 1: Create inactive workflow with Manual Trigger and 3-hour Schedule Trigger**

Settings: error workflow `64S3vgFFDl7a2yHT`, Europe/Stockholm, execution timeout 120s, all production execution saving off.

- [ ] **Step 2: Load only bounded context**

Input caps per run:

```text
ACTIVE goals: all
ACTIVE hunts: all
CURRENT context: max 60 rows, ranked by relevance/type
AI Radar signals: max 20 items where status in ALERT/BRIEF/WATCH and last_seen_at within 14 days
Existing opportunities: max 100 recent rows for dedupe/title/entity history
```

Do not include customer-level order data.

- [ ] **Step 3: Create six generation lanes**

The generation prompt must create candidates tagged with one or more exact origins:

```text
GOAL_HUNTER
PROBLEM_SOLVER
ASSET_RECOMBINER
INNOVATION_MATCHER
PROCESS_MINER
SERENDIPITY
```

The model may return at most 12 candidates/run and at most 4 from any one lane.

- [ ] **Step 4: Use this candidate JSON contract**

```json
{
  "title":"Kort konkret idé",
  "simple_summary":"2–3 meningar på svenska",
  "why_now":"Varför detta är relevant nu",
  "goal_ids":["CG-REVENUE"],
  "origin_types":["ASSET_RECOMBINER"],
  "source_refs":["https://..."],
  "asset_links":["kundbas","klubbnätverk"],
  "hypothesis":"Vad som måste vara sant för att idén ska fungera",
  "implementation_target_hint":"verifierat target eller NO_VERIFIED_TARGET",
  "pricing_summary":"Unknown - verify"
}
```

Rules:
- Swedish user-facing prose.
- No made-up price, savings, API, file path, workflow, market size, conversion effect, or partner capability.
- A candidate with no source can exist as a hypothesis, but must say so.
- `source_refs` may contain AI Radar source URLs or internal context refs; it may be empty for Serendipity hypotheses.
- `goal_ids` may be empty only for a high-leverage Serendipity candidate.

- [ ] **Step 5: Build deterministic IDs**

Normalize title + primary asset/technology and create:

```js
dedupe_key = sha256(normalizedConcept)
opportunity_id = "OP-" + sha256(dedupe_key).slice(0,12)
```

Do not use timestamps in either key.

- [ ] **Step 6: Dedupe before insert**

If an existing row has the same `dedupe_key`:
- update `last_seen_at`,
- merge any genuinely new source refs,
- keep prior ratings/actions/status,
- set `research_status="RESEARCH_PENDING"` again only if a materially new source ref or source content hash exists.

If no match: insert new candidate with:
- `business_value=0`
- `jonas_fit=50`
- `confidence=0`
- `research_status="RESEARCH_PENDING"`
- `decision_status="CANDIDATE"`

- [ ] **Step 7: Test duplicate suppression**

Pin two candidates with different wording but the same deterministic normalized concept.

Expected: one opportunity row/key, not two.

- [ ] **Step 8: Test lane diversity**

Pin model output with eight GOAL_HUNTER candidates and one ASSET_RECOMBINER candidate.

Expected: deterministic lane cap keeps max four GOAL_HUNTER candidates and preserves the other lane.

- [ ] **Step 9: Publish after tests pass**

Run once live. Verify no Discord call exists in workflow 52.

### Task 3: Build `53 OS – Evidence Enricher`

**Objects:**
- Create n8n workflow: `53 OS – Evidence Enricher`

**Interfaces:**
- Consumes: up to 3 `RESEARCH_PENDING` opportunities/run.
- Produces: structured evidence and `research_status="READY_FOR_JUDGE"`.

- [ ] **Step 1: Create inactive workflow with Manual Trigger and hourly Schedule Trigger at minute 20**

Use the standard OS production settings; execution timeout 180s.

- [ ] **Step 2: Select at most three candidates**

Sort by:
1. active-goal overlap count,
2. recency,
3. presence of direct source refs.

Do not use Jonas Fit here.

- [ ] **Step 3: Fetch source evidence directly**

For every HTTP(S) source ref:
- allow HTTPS only,
- timeout each request,
- cap body used by AI to 12,000 characters/source,
- keep max 5 sources/candidate,
- store source URL + fetched timestamp + short evidence excerpt/hash.

When a source is unreachable, store `fetch_status="FAILED"`; do not substitute an invented statement.

- [ ] **Step 4: Add internal evidence**

Attach only relevant context rows from `GK_OS_CONTEXT`:
- goals,
- verified tools/systems,
- known current process,
- prior related opportunities.

Limit total internal context text to 12,000 characters.

- [ ] **Step 5: Run Evidence Analyst**

Return exactly:

```json
{
  "what_is_verified":["..."],
  "what_is_unverified":["..."],
  "pricing_summary":"...",
  "monthly_cost_est":0,
  "implementation_target":"...",
  "evidence_grade":"STRONG|MEDIUM|WEAK",
  "confidence":0.0,
  "source_assessments":[
    {"source_ref":"...","supports":"...","status":"OK|FAILED|PARTIAL"}
  ]
}
```

Gate:
- STRONG requires at least one primary/direct source and no material contradiction.
- MEDIUM requires useful support but one or more material gaps.
- WEAK means the core proposition is not externally verified or rests mainly on model inference.

- [ ] **Step 6: Enforce price safety**

If actual pricing is not present in fetched evidence, force:
- `pricing_summary="Unknown - verify"`
- `monthly_cost_est=0`
- cap `evidence_grade` at MEDIUM.

- [ ] **Step 7: Persist evidence**

Write `evidence_json`, `pricing_summary`, `monthly_cost_est`, `implementation_target`, `evidence_grade`, `confidence`, `research_status="READY_FOR_JUDGE"`, `updated_at`.

- [ ] **Step 8: Test failed source behavior**

Pin an HTTP source failure and a model response claiming the source verified pricing.

Expected: validator keeps the failed source status, pricing becomes `Unknown - verify`, and grade cannot be STRONG.

- [ ] **Step 9: Test direct-source success**

Pin one official source with explicit capability and price.

Expected: structured evidence retains source ref, capability, price, and may reach STRONG if no contradiction.

- [ ] **Step 10: Publish after tests pass**

No Discord output and no external write beyond OS tables.

### Task 4: Build `54 OS – Opportunity Judge`

**Objects:**
- Create n8n workflow: `54 OS – Opportunity Judge`

**Interfaces:**
- Consumes: up to 3 `READY_FOR_JUDGE` opportunities.
- Produces: scored opportunities with `decision_status` one of `READY_TO_PUBLISH`, `WATCH`, `DISMISSED`.

- [ ] **Step 1: Create inactive workflow with Manual Trigger and hourly Schedule Trigger at minute 35**

Use standard OS production settings; timeout 180s.

- [ ] **Step 2: Run objective Judge pass**

Judge must score 0–100 components:

```json
{
  "goal_impact":0,
  "economic_potential":0,
  "time_to_value":0,
  "evidence_strength":0,
  "effort_inverse":0,
  "cost_inverse":0,
  "strategic_leverage":0,
  "reversibility":0,
  "cross_goal_leverage":0
}
```

Use deterministic weighting:

```text
goal_impact          20%
economic_potential   20%
time_to_value        10%
evidence_strength    15%
effort_inverse       10%
cost_inverse         10%
strategic_leverage    5%
reversibility         5%
cross_goal_leverage   5%
```

- [ ] **Step 3: Run separate Skeptic pass**

The Skeptic must receive the candidate + evidence + Judge output and return:

```json
{
  "verdict":"PASS|DOWNGRADE|DISMISS",
  "material_risks":["..."],
  "simpler_alternative":"...",
  "unsupported_claims":["..."],
  "reason":"..."
}
```

The Skeptic prompt must explicitly try to falsify the candidate rather than improve it.

- [ ] **Step 4: Apply deterministic final gate**

Rules:

```text
DISMISS:
- skeptic verdict DISMISS, OR
- Business Value < 50, OR
- confidence < 0.45.

WATCH:
- Business Value 50–69, OR
- evidence WEAK, OR
- skeptic DOWNGRADE causing final score below 70.

READY_TO_PUBLISH:
- Business Value >= 70,
- confidence >= 0.60,
- evidence grade STRONG or MEDIUM,
- skeptic verdict PASS or non-fatal DOWNGRADE,
- clear recommendation and at least one goal/asset rationale.
```

A candidate may be READY_TO_PUBLISH with unknown price, but `BYGG` later must fail closed before paid activation.

- [ ] **Step 5: Create implementation/build plan**

For every READY_TO_PUBLISH row, store 4–8 concrete steps in `build_plan_json`.

Mandatory contents:
1. exact verified target or first discovery target,
2. smallest useful change,
3. automated/observable test,
4. success metric,
5. rollback/fallback.

Never invent a target. Use `NO_VERIFIED_TARGET` if none is established.

- [ ] **Step 6: Create metric plan**

Store one or more measurable post-build outcomes in `metric_plan_json`, for example:

```json
[
  {"metric_name":"manual_minutes_per_case","baseline_source":"current process sample","expected_direction":"down","measure_after_days":7},
  {"metric_name":"conversion_rate","baseline_source":"Clarity/Shopify baseline","expected_direction":"up","measure_after_days":30}
]
```

Only include metrics with a plausible source.

- [ ] **Step 7: Generate stored plain-language fields**

The Judge may draft:
- `simple_summary`
- `why_now`
- `recommendation`

but must not write final Discord copy. That happens in 55.

- [ ] **Step 8: Test Skeptic downgrade**

Pin Judge score 88 and Skeptic verdict DISMISS with a material unsupported claim.

Expected: final `decision_status="DISMISSED"`.

- [ ] **Step 9: Test strong candidate**

Pin Business Value components that calculate to >= 80, MEDIUM/STRONG evidence, confidence >= 0.8, Skeptic PASS.

Expected: `READY_TO_PUBLISH`, stored build plan, stored metric plan.

- [ ] **Step 10: Publish workflow**

Run once live and verify no user-facing Discord post is produced yet.

### Task 5: Portfoliobalance and recheck behavior

**Objects:**
- Modify workflow: `54 OS – Opportunity Judge`
- Modify table state only: `GK_OS_OPPORTUNITIES`

**Interfaces:**
- Produces: diversity-aware READY_TO_PUBLISH queue and safe rechecks.

- [ ] **Step 1: Add daily category/origin caps**

Before setting READY_TO_PUBLISH, examine opportunities published/queued in the previous 7 days.

If three or more opportunities from the same dominant origin/category are already queued/published, require Business Value >= 85 for another from that same lane unless no other active goal has a qualified candidate.

- [ ] **Step 2: Set recheck windows**

```text
DISMISSED due to weak economics/evidence: recheck_after = +90 days
WATCH due to missing evidence/immaturity: recheck_after = +30 days
Duplicate/no material change: do not create a new row
```

- [ ] **Step 3: Test diversity gate**

Pin four otherwise publishable automation candidates and one new-revenue candidate with Business Value 78.

Expected: the new-revenue candidate remains eligible; the fourth repetitive automation candidate requires >=85 or is WATCH.

### Task 6: Phase 2 verification

- [ ] **Step 1: Run one controlled end-to-end test with a historical AI Radar item**

Use a known low-value patch release.

Expected: it does not become READY_TO_PUBLISH merely because it is new.

- [ ] **Step 2: Run one controlled internal idea test**

Use a candidate combining existing Golfkuponger assets with a strategic goal.

Expected: if evidence is partly inferential, it can be READY_TO_PUBLISH only at MEDIUM evidence with explicit assumptions; no fabricated facts.

- [ ] **Step 3: Verify cost**

Confirm generation runs broad/cheap and Evidence/Judge runs only on bounded candidate counts.

- [ ] **Step 4: Record workflow IDs and table ID in implementation notes**

These identifiers become fixed inputs for the Discord plan.
