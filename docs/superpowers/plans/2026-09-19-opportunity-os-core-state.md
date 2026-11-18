# Opportunity OS Core State + Goal/Context Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the durable goal, hunt, and context state that all later Opportunity OS workflows read from.

**Architecture:** Keep Company Brain and Growth System as source-of-truth inputs, but mirror only compact, structured state into n8n Data Tables for cheap autonomous reasoning. A weekly Goal Strategist proposes strategic goals and manages hunt areas; a daily Context Snapshot refreshes only changed context using content hashes.

**Tech Stack:** n8n on Railway/Postgres, n8n Data Tables, Notion credential `40eV72ZWKVMH8Nn3`, OpenRouter credential `C4g2PpsQvoz6k0uq`, JavaScript Code nodes.

**Spec:** `docs/superpowers/specs/2026-09-19-opportunity-os-design.md`

## Global Constraints

- Strategic goals may be proposed by AI but become ACTIVE only after Jonas activates them.
- Company Brain remains the source of stable operational truth; Growth System remains the source for opportunities, experiments, and learning.
- Existing AI Radar workflows 30–37 remain active during this phase.
- Production execution saving remains off after QA.
- Shared error workflow: `64S3vgFFDl7a2yHT`.
- Timezone: `Europe/Stockholm`.
- No Shopify MAIN writes.
- New external paid services are not activated in this phase.

## Review Focus

1. A proposed strategic goal must never become ACTIVE merely because the model returned it.
2. A context source that has not changed must not rewrite its row or trigger downstream work.
3. Missing/unreachable context sources must create a visible `CONTEXT_GAP` row instead of being silently treated as current truth.
4. Duplicate goals/hunts must upsert by deterministic IDs, not create extra rows.
5. Model output containing unknown goal levels/statuses must be rejected before persistence.

---

### Task 1: Create OS core Data Tables

**Objects:**
- Create Data Table: `GK_OS_GOALS`
- Create Data Table: `GK_OS_HUNTS`
- Create Data Table: `GK_OS_CONTEXT`

**Interfaces:**
- Produces: exact schemas below for workflows 50–59.

- [ ] **Step 1: Confirm the three tables do not already exist**

Run `search_data_tables(projectId="zoZ6lq8bWNd3jueo", query="GK_OS_", limit=100)`.

Expected: none of `GK_OS_GOALS`, `GK_OS_HUNTS`, `GK_OS_CONTEXT` exists.

- [ ] **Step 2: Create `GK_OS_GOALS` with the exact schema**

```json
[
  {"name":"goal_id","type":"string"},
  {"name":"title","type":"string"},
  {"name":"level","type":"string"},
  {"name":"parent_goal_id","type":"string"},
  {"name":"status","type":"string"},
  {"name":"source","type":"string"},
  {"name":"rationale","type":"string"},
  {"name":"success_definition","type":"string"},
  {"name":"priority_score","type":"number"},
  {"name":"content_hash","type":"string"},
  {"name":"created_at","type":"date"},
  {"name":"last_reviewed_at","type":"date"},
  {"name":"activated_by","type":"string"},
  {"name":"activated_at","type":"date"}
]
```

- [ ] **Step 3: Create `GK_OS_HUNTS` with the exact schema**

```json
[
  {"name":"hunt_id","type":"string"},
  {"name":"goal_id","type":"string"},
  {"name":"title","type":"string"},
  {"name":"reason","type":"string"},
  {"name":"status","type":"string"},
  {"name":"research_weight","type":"number"},
  {"name":"query_strategy_json","type":"string"},
  {"name":"content_hash","type":"string"},
  {"name":"created_at","type":"date"},
  {"name":"updated_at","type":"date"},
  {"name":"last_run_at","type":"date"},
  {"name":"next_run_at","type":"date"}
]
```

- [ ] **Step 4: Create `GK_OS_CONTEXT` with the exact schema**

```json
[
  {"name":"context_key","type":"string"},
  {"name":"context_type","type":"string"},
  {"name":"title","type":"string"},
  {"name":"summary","type":"string"},
  {"name":"source_ref","type":"string"},
  {"name":"content_hash","type":"string"},
  {"name":"status","type":"string"},
  {"name":"verified_at","type":"date"},
  {"name":"updated_at","type":"date"}
]
```

- [ ] **Step 5: Verify schemas**

Run `search_data_tables(projectId="zoZ6lq8bWNd3jueo", query="GK_OS_", limit=100)`.

Expected: all three tables exist and every column name/type matches the JSON above exactly.

### Task 2: Seed company goals and strategic goal proposals

**Objects:**
- Modify Data Table: `GK_OS_GOALS`

**Interfaces:**
- Produces: ACTIVE company goals and PROPOSED strategic goals.

- [ ] **Step 1: Insert four ACTIVE company goals sourced from the existing Growth System**

Use deterministic IDs:

```json
[
  {"goal_id":"CG-REVENUE","title":"Öka omsättning","level":"COMPANY","parent_goal_id":"","status":"ACTIVE","source":"GROWTH_SYSTEM","rationale":"Growth System anger ökad omsättning som ett kärnsyfte.","success_definition":"Mätbar ökning av intäkter utan oproportionerlig kostnadsökning.","priority_score":100},
  {"goal_id":"CG-PROFIT","title":"Öka lönsamhet","level":"COMPANY","parent_goal_id":"","status":"ACTIVE","source":"GROWTH_SYSTEM","rationale":"Growth System anger ökad lönsamhet som ett kärnsyfte.","success_definition":"Ökat bidrag/resultat genom högre intäkt, lägre kostnad eller båda.","priority_score":100},
  {"goal_id":"CG-CONVERSION","title":"Öka konvertering","level":"COMPANY","parent_goal_id":"","status":"ACTIVE","source":"GROWTH_SYSTEM","rationale":"Growth System anger konvertering som ett kärnsyfte.","success_definition":"Fler relevanta besökare genomför önskad handling.","priority_score":90},
  {"goal_id":"CG-RETENTION","title":"Öka återköp och kundvärde","level":"COMPANY","parent_goal_id":"","status":"ACTIVE","source":"GROWTH_SYSTEM","rationale":"Growth System anger återköp och kundvärde som kärnsyften.","success_definition":"Ökad återköpsgrad, högre kundvärde eller lägre churn.","priority_score":90}
]
```

Populate `content_hash`, `created_at`, and `last_reviewed_at` at write time.

- [ ] **Step 2: Insert strategic goals as PROPOSED, not ACTIVE**

```json
[
  {"goal_id":"SG-ALT-REVENUE","title":"Hitta alternativa intäktskällor","level":"STRATEGIC","parent_goal_id":"CG-REVENUE","status":"PROPOSED","source":"JONAS_CHAT","rationale":"Jonas vill att systemet hittar nya enkla sätt att skapa intäkter med Golfkupongers befintliga tillgångar och ny teknik.","success_definition":"Minst en verifierad ny intäktskälla med positiv enhetsekonomi.","priority_score":85},
  {"goal_id":"SG-BEST-WEB","title":"Ha bästa möjliga hemsida","level":"STRATEGIC","parent_goal_id":"CG-CONVERSION","status":"PROPOSED","source":"JONAS_CHAT","rationale":"Jonas vill att systemet kontinuerligt hittar förbättringar i styling, snabbhet, UX, CRO och teknik.","success_definition":"Kontinuerligt förbättrade webbmått och kvalitetsindikatorer jämfört med egen baseline.","priority_score":85},
  {"goal_id":"SG-AUTOMATION","title":"Automatisera manuellt arbete","level":"STRATEGIC","parent_goal_id":"CG-PROFIT","status":"PROPOSED","source":"JONAS_CHAT","rationale":"Minska återkommande manuellt arbete och frigör tid.","success_definition":"Mätbar tidsbesparing med bibehållen eller förbättrad kvalitet.","priority_score":80},
  {"goal_id":"SG-PARTNERS","title":"Öka distribution och partners","level":"STRATEGIC","parent_goal_id":"CG-REVENUE","status":"PROPOSED","source":"GROWTH_SYSTEM","rationale":"Fler relevanta distributionskanaler och partners kan öka räckvidd och försäljning.","success_definition":"Fler aktiva partnerkanaler som genererar mätbar försäljning.","priority_score":75}
]
```

- [ ] **Step 3: Verify activation boundary**

Read `GK_OS_GOALS`.

Expected: only `CG-*` rows are ACTIVE; every `SG-*` row is PROPOSED with empty `activated_by` and `activated_at`.

### Task 3: Build `51 OS – Context Snapshot`

**Objects:**
- Create n8n workflow: `51 OS – Context Snapshot`
- Folder: `30 AI RADAR` (`NXv5tH5JyNYNUY9t`)

**Interfaces:**
- Consumes: Notion company knowledge, Growth System, current AI Radar tables, known system inventory.
- Produces: normalized rows in `GK_OS_CONTEXT` keyed by `context_key`.

- [ ] **Step 1: Create the workflow inactive with Manual Trigger and daily Schedule Trigger at 05:30 Europe/Stockholm**

Settings:

```json
{
  "executionOrder":"v1",
  "errorWorkflow":"64S3vgFFDl7a2yHT",
  "timezone":"Europe/Stockholm",
  "saveExecutionProgress":false,
  "saveManualExecutions":false,
  "saveDataErrorExecution":"none",
  "saveDataSuccessExecution":"none",
  "executionTimeout":120
}
```

- [ ] **Step 2: Add source readers**

The workflow must read these source classes independently:

```text
company_brain     -> Notion Company Brain
growth_system     -> Notion Growth System / Growth Radar
ai_radar          -> GK_AI_RADAR_ITEMS + GK_AI_RADAR_CONFIG
workflow_inventory-> verified static inventory initially, including workflow IDs 30–37
repos             -> ulle73/golfkuponger-app and ulle73/content-engine metadata when reachable
orders            -> aggregate-only signals from GK_ORDERS; no customer PII copied into GK_OS_CONTEXT
```

If a live source is unavailable, emit a context item with `status="CONTEXT_GAP"` and a concise reason.

- [ ] **Step 3: Normalize source output**

Each context row emitted by the normalization Code node must have exactly:

```js
{
  context_key: string,
  context_type: "company_brain" | "growth_system" | "ai_radar" | "workflow_inventory" | "repo" | "orders" | "context_gap",
  title: string,
  summary: string,
  source_ref: string,
  content_hash: string,
  status: "CURRENT" | "CONTEXT_GAP",
  verified_at: string,
  updated_at: string
}
```

Use SHA-256 over `context_type + title + summary + source_ref` for `content_hash`.

- [ ] **Step 4: Skip unchanged rows before write**

Load existing `GK_OS_CONTEXT` row by `context_key`; only upsert when `content_hash` differs or existing status differs.

- [ ] **Step 5: Add PII guard test**

Create pin data containing an order aggregate and a fake customer email.

Expected: normalized context may include order counts/totals but must not include the fake email, name, phone, or raw order payload.

- [ ] **Step 6: Test the workflow**

Use `prepare_workflow_pin_data`, then `test_workflow`.

Expected: SUCCESS; unchanged hashes route around the upsert node; a missing source produces `CONTEXT_GAP`.

- [ ] **Step 7: Publish and run once live**

Publish only after validation passes. Run once with live read-only sources.

Expected: `GK_OS_CONTEXT` contains CURRENT rows plus explicit gaps, with no PII.

### Task 4: Build `50 OS – Goal Strategist`

**Objects:**
- Create n8n workflow: `50 OS – Goal Strategist`
- Reads: `GK_OS_GOALS`, `GK_OS_HUNTS`, `GK_OS_CONTEXT`
- Uses: OpenRouter `openrouter/free`

**Interfaces:**
- Produces: PROPOSED strategic goals and ACTIVE hunts only under ACTIVE strategic goals.

- [ ] **Step 1: Create inactive workflow with Manual Trigger and weekly Schedule Trigger Monday 06:15 Europe/Stockholm**

Use the same production settings as Task 3 with `executionTimeout=120`.

- [ ] **Step 2: Build compact strategist input**

Load:
- all ACTIVE company goals,
- ACTIVE + PROPOSED strategic goals,
- ACTIVE hunts,
- CURRENT context summaries,
- up to 20 most recent outcome/opportunity learnings once those tables exist; for this phase, an empty array is valid.

- [ ] **Step 3: Add Goal Strategist prompt contract**

Require JSON only:

```json
{
  "proposed_goals":[
    {
      "goal_id":"SG-...",
      "title":"...",
      "parent_goal_id":"CG-...",
      "rationale":"...",
      "success_definition":"...",
      "priority_score":0
    }
  ],
  "hunt_changes":[
    {
      "hunt_id":"H-...",
      "goal_id":"SG-...",
      "title":"...",
      "reason":"...",
      "status":"ACTIVE",
      "research_weight":0,
      "query_strategy":["..."]
    }
  ]
}
```

Rules:
- max 3 new strategic goal proposals/run,
- goal IDs deterministic from normalized title,
- proposed goals are always `PROPOSED`,
- hunts may be ACTIVE only when their parent strategic goal is already ACTIVE in stored state,
- never activate a goal from model output.

- [ ] **Step 4: Add deterministic validator**

Reject any generated object where:
- `parent_goal_id` is not an existing COMPANY goal,
- `priority_score` is outside 0–100,
- `research_weight` is outside 0–100,
- hunt parent is not ACTIVE,
- model attempts `status=ACTIVE` for a strategic goal.

- [ ] **Step 5: Upsert goal proposals and hunts**

Goals upsert by `goal_id`; hunts upsert by `hunt_id`. Preserve `activated_by` and `activated_at` on every AI update.

- [ ] **Step 6: Test the activation boundary**

Pin one PROPOSED strategic goal and model output that tries to create an ACTIVE hunt beneath it.

Expected: the hunt is rejected and no ACTIVE hunt row is written.

- [ ] **Step 7: Test legitimate hunt creation**

Pin one ACTIVE strategic goal and valid hunt output.

Expected: exactly one ACTIVE hunt is produced with `query_strategy_json` as a JSON array.

- [ ] **Step 8: Publish after tests pass**

Run once live.

Expected: new strategic ideas appear as PROPOSED only; no new strategic goal becomes ACTIVE.

### Task 5: Phase 1 verification and documentation

**Files:**
- Modify: `docs/superpowers/specs/2026-09-19-opportunity-os-design.md` only if implementation reveals a factual interface change.

- [ ] **Step 1: Verify all three Data Tables with `search_data_tables`**

Expected: schemas exactly match Task 1.

- [ ] **Step 2: Verify workflows 50 and 51**

Expected: both published, correct timezone/error workflow, production execution saving off.

- [ ] **Step 3: Verify one live context refresh does not rewrite unchanged rows**

Capture `updatedAt` for one row, rerun 51 with unchanged source, re-read row.

Expected: `updatedAt` remains unchanged.

- [ ] **Step 4: Commit plan-related documentation changes**

If the spec did not change, no spec commit is needed. Record workflow IDs/table IDs in the implementation log and in the next plan's interface section.
