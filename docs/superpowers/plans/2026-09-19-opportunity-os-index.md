# Golfkuponger Opportunity OS — Implementation Plan Index

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved Opportunity OS design in five independently testable phases without disrupting the current AI Radar until the replacement is proven.

**Architecture:** Build durable state first, then the opportunity engine, then the Discord decision surface, then autonomous build execution, then outcome learning and cutover. Each phase has its own acceptance gate so failures do not contaminate later phases.

**Tech Stack:** n8n/Railway/Postgres, n8n Data Tables, Notion, OpenRouter, Discord, GitHub, Node.js/TypeScript, Codex SDK, Shopify/Railway/n8n APIs for authenticated build adapters.

**Spec:** `docs/superpowers/specs/2026-09-19-opportunity-os-design.md`

## Global Constraints

- Current workflows 30–37 remain intact until the cutover plan explicitly disables direct Radar publishing.
- Shopify MAIN always requires separate Jonas approval.
- Only Jonas Discord ID `388380559606546432` may rate or mutate decisions.
- Nicholas may read all main cards and MER INFO.
- No TESTA button exists in the new UX.
- Objective Business Value and Jonas Fit remain separate.
- New paid-service activation defaults to a 0 SEK/month autonomous spend limit.
- Missing capabilities, credentials, measurements, or evidence fail closed.
- Production execution saving is off after QA.

## Review Focus

1. Phase interfaces must use exact Data Table/workflow IDs created by previous phases, not copied guesses.
2. Existing AI Radar messages/buttons must remain functional during the migration window.
3. The build worker must stay inactive when no real deployment adapter is credential-ready.
4. Cutover must be reversible by re-enabling workflow 32.
5. Outcome/self-optimization must not feed personal preference into objective Business Value.

---

## Execution order

### Phase 1 — Core state, goals, context

Plan: `docs/superpowers/plans/2026-09-19-opportunity-os-core-state.md`

Deliverables:
- `GK_OS_GOALS`
- `GK_OS_HUNTS`
- `GK_OS_CONTEXT`
- `50 OS – Goal Strategist`
- `51 OS – Context Snapshot`

Gate: strategic goals cannot self-activate; context is compact, current, deduped, and PII-safe.

### Phase 2 — Opportunity generation, evidence, judgment

Plan: `docs/superpowers/plans/2026-09-19-opportunity-os-opportunity-engine.md`

Deliverables:
- `GK_OS_OPPORTUNITIES`
- `52 OS – Opportunity Generator`
- `53 OS – Evidence Enricher`
- `54 OS – Opportunity Judge`

Gate: a candidate cannot reach READY_TO_PUBLISH without objective scoring, evidence handling, and a separate skeptic pass.

### Phase 3 — Pedagogical Discord UX and feedback

Plan: `docs/superpowers/plans/2026-09-19-opportunity-os-discord.md`

Deliverables:
- `GK_OS_FEEDBACK`
- `GK_OS_ACTIONS`
- `55 OS – Opportunity Publisher`
- `56 OS – Discord Interactions`
- OS routes added to signed workflow 37

Gate: Nicholas can understand/read; only Jonas can rate/act; MER INFO makes no extra AI call.

### Phase 4 — Autonomous BUILD execution

Plan: `docs/superpowers/plans/2026-09-19-opportunity-os-build-orchestrator.md`

Deliverables:
- `GK_OS_BUILD_JOBS`
- `57 OS – Build Orchestrator`
- `ulle73/golfkuponger-opportunity-worker`
- Railway `opportunity-os-worker`
- Codex + GitHub/n8n/Railway/Shopify adapter layer

Gate: one reversible end-to-end job succeeds; replay is idempotent; verification failure rolls back; Shopify MAIN blocks for separate approval.

### Phase 5 — Outcomes, learning, safe cutover

Plan: `docs/superpowers/plans/2026-09-19-opportunity-os-outcomes-cutover.md`

Deliverables:
- `GK_OS_OUTCOMES`
- `GK_OS_CONFIG`
- `58 OS – Outcome Tracker`
- `59 OS – Self Optimizer`
- shadow comparison
- safe cutover from workflow 32 user-facing publishing

Gate: at least one measurable/explicitly-unknown outcome path works; optimizer stays within hard bounds; OS production post works before Radar Publisher is disabled.

## Cross-phase interface contract

```text
GOALS/HUNTS/CONTEXT
        ↓
52 GENERATOR
        ↓
GK_OS_OPPORTUNITIES
        ↓
53 EVIDENCE
        ↓
54 JUDGE + SKEPTIC
        ↓
55 PUBLISHER
        ↓
37 SIGNATURE ROUTER → 56 INTERACTIONS
        ↓
GK_OS_FEEDBACK / GK_OS_ACTIONS
        ↓
57 BUILD ORCHESTRATOR → BUILD WORKER
        ↓
GK_OS_BUILD_JOBS
        ↓
58 OUTCOMES
        ↓
59 SELF OPTIMIZER
        ↺ goals/hunts/research weights
```

## Commit strategy

Each independently testable task gets its own commit. Do not mix:
- data schema changes,
- workflow creation,
- Discord router changes,
- worker service code,
- cutover changes

in the same commit unless a testable interface requires them together.

## Rollback strategy

- Phase 1–3: new OS objects can be disabled without changing existing Radar behavior.
- Phase 4: worker is isolated; workflow 57 can be disabled and pending jobs preserved.
- Phase 5: cutover rollback is re-enable workflow 32 and set OS publisher shadow mode back to true.
- Historical tables are retained throughout.

## Completion condition

Opportunity OS is complete only after all five phase acceptance gates pass. Creating workflows/tables alone is not completion.
