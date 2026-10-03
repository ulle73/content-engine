# Opportunity OS Discord UX + Feedback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace technical AI Radar output with extremely simple, pedagogical Opportunity OS cards while preserving Jonas-only 1–10 learning and action control.

**Architecture:** Workflow 55 publishes opportunities/goals to the existing Discord bot/channel. The existing signed interaction workflow 37 remains the sole public Discord interaction endpoint and forwards Opportunity OS button events to a new internal workflow 56. Nicholas may read cards and use MER INFO, but only Jonas may rate or take actions.

**Tech Stack:** n8n, Discord bot credential `2Pwo6eNhWtKkqI7C`, existing Discord application/signature verification in workflow `STLjMHAQZxbQ0r6r`, n8n Data Tables.

**Spec:** `docs/superpowers/specs/2026-09-19-opportunity-os-design.md`

## Global Constraints

- Main cards target 60–100 words and have an absolute maximum of about 140 words.
- Main cards must avoid unexplained technical language.
- Technical scores, implementation target, repo/workflow IDs, confidence, and full build plans do not appear in the main card.
- MER INFO uses stored analysis; it must not trigger another AI call.
- Jonas Discord user ID `388380559606546432` is the only user allowed to rate or create actions.
- Nicholas and other readers may use MER INFO.
- There is no TESTA button.
- Existing AI Radar interaction endpoint remains valid during migration.
- Existing 30–37 workflows stay available until cutover is verified.

## Review Focus

1. A non-Jonas user clicking a rating or action must not mutate any table.
2. MER INFO must work for Nicholas/readers without granting decision rights.
3. Discord custom IDs must stay under Discord limits and parse deterministically.
4. A technically complex opportunity must still render in plain Swedish with no hidden-score leakage.
5. Publisher retries must not post the same opportunity twice.

---

### Task 1: Create feedback and action tables

**Objects:**
- Create Data Table: `GK_OS_FEEDBACK`
- Create Data Table: `GK_OS_ACTIONS`

**Interfaces:**
- Produces: durable Jonas ratings and explicit actions for workflows 56–59.

- [ ] **Step 1: Create `GK_OS_FEEDBACK`**

```json
[
  {"name":"feedback_key","type":"string"},
  {"name":"entity_type","type":"string"},
  {"name":"entity_id","type":"string"},
  {"name":"jonas_rating","type":"number"},
  {"name":"discord_message_id","type":"string"},
  {"name":"interaction_id","type":"string"},
  {"name":"rated_at","type":"date"},
  {"name":"processed_at","type":"date"}
]
```

- [ ] **Step 2: Create `GK_OS_ACTIONS`**

```json
[
  {"name":"action_key","type":"string"},
  {"name":"entity_type","type":"string"},
  {"name":"entity_id","type":"string"},
  {"name":"action","type":"string"},
  {"name":"user_id","type":"string"},
  {"name":"discord_message_id","type":"string"},
  {"name":"interaction_id","type":"string"},
  {"name":"actioned_at","type":"date"},
  {"name":"processed_at","type":"date"},
  {"name":"status","type":"string"},
  {"name":"result_ref","type":"string"},
  {"name":"error","type":"string"}
]
```

- [ ] **Step 3: Verify schemas**

Expected: exact column names/types above.

### Task 2: Build `55 OS – Opportunity Publisher`

**Objects:**
- Create n8n workflow: `55 OS – Opportunity Publisher`
- Uses Discord credential: `2Pwo6eNhWtKkqI7C`
- Initial destination: existing `#ai-radar` channel ID `1550641582208712806`

**Interfaces:**
- Consumes: `GK_OS_OPPORTUNITIES` rows where `decision_status="READY_TO_PUBLISH"` and no `published_at`.
- Consumes: `GK_OS_GOALS` where `level="STRATEGIC"`, `status="PROPOSED"`, and not yet surfaced.
- Produces: Discord message + persisted `discord_message_id` and `published_at`.

- [ ] **Step 1: Create inactive workflow with Manual Trigger and 30-minute Schedule Trigger**

Use standard OS settings; timeout 60s.

- [ ] **Step 2: Add publish guard**

Before formatting:
- max 3 Opportunity OS posts per local calendar day,
- max 2 posts per run,
- never publish a row with an existing `discord_message_id`,
- sort opportunities by objective Business Value first, then Jonas Fit as tie-breaker only,
- reserve at least one slot/day for a different goal/category when a qualified candidate exists.

- [ ] **Step 3: Add Plain Swedish Editor**

Input: stored `simple_summary`, `why_now`, `recommendation`, goal titles, cost/time summaries.

Output JSON:

```json
{
  "label":"💡 Ny möjlighet",
  "headline":"...",
  "body":"...",
  "why":"...",
  "recommendation":"...",
  "time_label":"~2 h",
  "cost_label":"Låg"
}
```

Hard rules:
- Swedish.
- Explain the business idea before the technology.
- No unexplained MCP, webhook, orchestration, deployment, embeddings, RAG, implementation target, confidence, score, repo path, workflow ID.
- If a technical term is unavoidable, explain it in the same sentence.
- 60–100 words target; <=140 words after formatting.
- Nicholas must understand the point without knowing how the system is built.

- [ ] **Step 4: Add deterministic post-copy validator**

Reject and return the row to `WATCH` with a validation reason if:
- total prose >140 words,
- body contains any banned technical term without a plain-language explanation,
- recommendation is missing,
- card claims numeric savings/cost not stored in the opportunity evidence.

- [ ] **Step 5: Format opportunity card**

Visible content:

```text
💡 <label>
**<headline>**

<body>

**Varför intressant?**
<why>

**Mitt förslag:** <recommendation>

Tid: <time_label> · Kostnad: <cost_label>

Hur intressant är detta för dig? 1–10
```

Do not render Business Value, Jonas Fit, confidence, implementation target, evidence grade, or technical details.

- [ ] **Step 6: Add opportunity component rows**

Row 1:
```text
[1] [2] [3] [4] [5]
```

Row 2:
```text
[6] [7] [8] [9] [10]
```

Custom IDs:
```text
osrate:1:<opportunity_id>
...
osrate:10:<opportunity_id>
```

Row 3:
```text
[ BYGG ] [ INTE NU ] [ MER INFO ]
```

Custom IDs:
```text
osaction:BUILD:<opportunity_id>
osaction:NO:<opportunity_id>
osmore:<opportunity_id>
```

- [ ] **Step 7: Format proposed-goal cards**

Visible content:

```text
🎯 **Nytt mål**
**<goal title>**

<plain-language rationale>

**Varför?**
<what this would help Golfkuponger achieve>

**Mitt förslag:** Gör målet aktivt så systemet börjar leta möjligheter löpande.
```

Buttons:
```text
[ AKTIVERA MÅL ] [ INTE NU ] [ MER INFO ]
```

Custom IDs:
```text
osgoal:ACTIVATE:<goal_id>
osgoal:NO:<goal_id>
osgoalmore:<goal_id>
```

Goal cards do not use 1–10; the 1–10 personal preference signal remains tied to opportunity ideas.

- [ ] **Step 8: Persist successful Discord result**

After Discord returns a message ID:
- set opportunity `discord_message_id`,
- set `published_at`,
- set `decision_status="PUBLISHED"`.

For goal proposals, persist a context marker `goal_surfaced:<goal_id>` in `GK_OS_CONTEXT` so the same unchanged proposal is not reposted.

- [ ] **Step 9: Test duplicate prevention**

Pin an already-published opportunity.

Expected: no Discord POST node receives the item.

- [ ] **Step 10: Test plain-language guard**

Pin copy containing `MCP orchestration via webhook` with no explanation.

Expected: validator blocks publish.

- [ ] **Step 11: Publish after tests pass**

Run one controlled post only after button handler in Task 4 is ready.

### Task 3: Build stored MER INFO payloads

**Objects:**
- Modify: workflow `54 OS – Opportunity Judge`
- Modify: table `GK_OS_OPPORTUNITIES`

**Interfaces:**
- Produces: `more_info_text` ready for Discord ephemeral response with no AI call.

- [ ] **Step 1: Generate a structured stored detail document**

Required sections, in this order:

```text
Vad är idén?
Vilket mål stödjer den?
Varför är den intressant nu?
Vad gör Golfkuponger idag?
Vad föreslår systemet?
Evidens och källor
Kostnad och tidsåtgång
Risker
Byggplan
Hur mäter vi resultatet?
Tekniska detaljer
```

- [ ] **Step 2: Keep business explanation first**

The first 70% of the text should be understandable without technical implementation knowledge.

- [ ] **Step 3: Store source refs as concise labels/URLs**

Do not copy large source excerpts into Discord details.

- [ ] **Step 4: Enforce Discord-safe size**

Store full details in the table, but 56 must split/truncate for Discord embed limits deterministically.

### Task 4: Build `56 OS – Discord Interactions` as an internal handler

**Objects:**
- Create n8n workflow: `56 OS – Discord Interactions`
- Modify existing signed public workflow: `37 AI – Discord Interactions v2` (`STLjMHAQZxbQ0r6r`)

**Interfaces:**
- 37 remains the only public Discord webhook and performs Ed25519 verification.
- 37 forwards parsed OS interactions to 56.
- 56 returns a Discord interaction response body to 37.

- [ ] **Step 1: Create workflow 56 with Execute Sub-workflow Trigger**

Input object contract:

```js
{
  kind: "rate" | "action" | "more" | "goal_action" | "goal_more",
  entity_id: string,
  rating?: number,
  action?: string,
  user_id: string,
  message_id: string,
  interaction_id: string,
  interaction_at: string
}
```

Output: a Discord response object with `type:4` and ephemeral `flags:64`.

- [ ] **Step 2: Add Jonas authorization gate**

```js
const JONAS_ID = "388380559606546432";
const mutating = ["rate","action","goal_action"].includes(kind);
if (mutating && user_id !== JONAS_ID) {
  return {
    type: 4,
    data: {
      flags: 64,
      content: "Du kan läsa allt, men endast Jonas kan ranka eller fatta beslut i systemet."
    }
  };
}
```

MER INFO and goal MER INFO remain readable by any Discord user with channel access.

- [ ] **Step 3: Save opportunity ratings**

Validate:
- entity ID pattern `^OP-[a-f0-9]{12}$`,
- integer rating 1–10.

Upsert by `entity_id` into `GK_OS_FEEDBACK`:

```text
feedback_key = opportunity:<entity_id>
entity_type = opportunity
entity_id = <entity_id>
jonas_rating = <1..10>
...
```

Return: `Betyg **N/10** sparat.`

- [ ] **Step 4: Save opportunity actions**

Allowed actions: `BUILD`, `NO`.

Upsert by `action_key="opportunity:<entity_id>"` into `GK_OS_ACTIONS`.

For BUILD:
- `status="PENDING"`
- response: `**BYGG** registrerat. Systemet tar nu idén vidare enligt den sparade planen.`

For NO:
- `status="DONE"`
- mark opportunity `decision_status="DECLINED"`
- response: `**INTE NU** sparat. Idén drivs inte vidare om inget materiellt förändras.`

- [ ] **Step 5: Activate goals**

Allowed goal action: `ACTIVATE`, `NO`.

ACTIVATE:
- load exact goal row,
- require `level="STRATEGIC"` and `status="PROPOSED"`,
- set `status="ACTIVE"`,
- `activated_by="JONAS_DISCORD"`,
- `activated_at=interaction_at`,
- return a concise confirmation.

NO:
- set `status="PAUSED"`,
- never delete the goal.

- [ ] **Step 6: Serve opportunity MER INFO**

Load `more_info_text` by entity ID.

Return ephemeral content/embed. No LLM node may be in this route.

- [ ] **Step 7: Serve goal MER INFO**

Load goal rationale, success definition, parent company goal, and current active hunts if any. Return plain Swedish.

### Task 5: Extend the signed public Discord router `37 AI – Discord Interactions v2`

**Objects:**
- Modify workflow: `STLjMHAQZxbQ0r6r`

**Interfaces:**
- Existing AI Radar routes remain functional during migration.
- New OS routes forward to workflow 56.

- [ ] **Step 1: Preserve current signature verification exactly**

Do not change:
- Ed25519 public key handling,
- raw-body verification,
- PING handling,
- Jonas ID.

- [ ] **Step 2: Add parsing branches before the existing unknown route**

Parse:

```text
osrate:<rating>:<OP-id>           -> kind=rate
osaction:<BUILD|NO>:<OP-id>       -> kind=action
osmore:<OP-id>                    -> kind=more
osgoal:<ACTIVATE|NO>:<goal-id>     -> kind=goal_action
osgoalmore:<goal-id>               -> kind=goal_more
```

- [ ] **Step 3: Forward only the normalized parsed object to 56**

Use Execute Sub-workflow and wait for completion.

- [ ] **Step 4: Respond to Discord with 56's returned object**

Keep public webhook response under Discord's interaction deadline.

- [ ] **Step 5: Regression-test existing AI Radar buttons**

Pin current `rate:`, `action:`, and `more:` interactions.

Expected: existing routes still behave unchanged until cutover.

- [ ] **Step 6: Test Nicholas behavior**

Pin a non-Jonas user:
- `osmore:<id>` -> details returned.
- `osrate:9:<id>` -> no mutation; authorization message.
- `osaction:BUILD:<id>` -> no mutation; authorization message.

### Task 6: Update personal preference learner

**Objects:**
- Modify workflow: `35 AI – Radar Preference Learner` or create an OS-specific preference section in `59 OS – Self Optimizer` later.
- Preferred in this phase: keep 35 unchanged and expose OS feedback for phase 5.

**Interfaces:**
- No objective Business Value score may be modified by rating data.

- [ ] **Step 1: Confirm OS feedback is stored independently**

Do not write OS ratings into `GK_AI_RADAR_FEEDBACK`.

- [ ] **Step 2: Add no score coupling in 54**

Verify `business_value` is computed without reading `GK_OS_FEEDBACK`.

- [ ] **Step 3: Leave `jonas_fit=50` until phase 5 learns enough samples**

This prevents a one-rating profile from distorting visibility.

### Task 7: Controlled Discord QA

- [ ] **Step 1: Temporarily publish one known synthetic Opportunity OS row**

Use a clearly labeled QA candidate with no external side effects.

- [ ] **Step 2: Verify card readability**

Check:
- <=140 words,
- no internal scores,
- no raw implementation target,
- no TESTA button,
- 1–10 visible,
- BYGG / INTE NU / MER INFO visible.

- [ ] **Step 3: Verify Jonas rating**

Click one 1–10 button.

Expected: one upserted `GK_OS_FEEDBACK` row.

- [ ] **Step 4: Verify MER INFO with a non-Jonas test identity if available**

Expected: details readable, no mutation.

- [ ] **Step 5: Verify BYGG only creates a PENDING action**

At this phase, workflow 57 is not active yet, so the action must be persisted but not executed.

- [ ] **Step 6: Remove/mark the QA candidate**

Set it to a non-publishable test state; do not delete real history.
