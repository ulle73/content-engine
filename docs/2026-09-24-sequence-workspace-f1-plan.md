# Sequence Workspace F1 — Project Workspace Ledger

**Date:** 2026-09-24  
**Status:** DONE — implemented, CI-verified and deployed 2026-09-24.  
**Depends on:** E1–E4 live Sequence Engine backend.

> F1 is a thin UI/read model over verified sequence services. It may create an empty SequenceProject, but it must not mutate anchors/clips/bridges or start provider generation.

## F1.1 Navigation and project list

- [x] Keep the six primary app destinations unchanged.
- [x] Add Sekvenser as a sub-tab under Media.
- [x] Sequence pages keep Media highlighted in desktop/mobile navigation.
- [x] Company-scoped project list shows status and anchor/clip/bridge counts.
- [x] Empty state explains what comes next.
- [x] User can create an empty company-scoped SequenceProject.
- [x] Project creation validates title, format, platform and bounded brief.
- [x] Creating a project performs no provider call.

## F1.2 Dedicated project workspace

- [x] Dedicated project URL scoped to the owning company.
- [x] Project header shows status, format and platform.
- [x] Summary shows anchor, clip, bridge and candidate counts.
- [x] Timeline shows canonical anchor order.
- [x] Anchor card shows thumbnail, K-position, locked/unlocked state and source provenance.
- [x] Clip cards show status, recipe, candidate count and selected version/model.
- [x] Bridge cards are visually distinct and show source clip pair.
- [x] Segment status table shows selected generation status.
- [x] Empty projects render safely.

## F1.3 Safety boundary

- [x] No regenerate action.
- [x] No anchor replace action.
- [x] No provider preview/start action.
- [x] No paid generation action.
- [x] No sequence domain rule is duplicated in template code.
- [x] Cross-company project lookup returns 404.
- [x] Existing E1–E4 services/models remain source of truth.

## F1.4 Responsive/accessibility baseline

- [x] Desktop timeline uses native horizontal overflow rather than custom carousel JS.
- [x] Mobile timeline stacks vertically.
- [x] Lock state is text, not color-only.
- [x] Timeline has semantic labels/roles.
- [x] Status table remains scrollable on narrow screens.
- [x] Native details/summary used for project-create disclosure.

## Release gates

- [x] No migration required.
- [x] `makemigrations --check --dry-run` passes.
- [x] Full normal Django suite passes.
- [x] Full PostgreSQL suite passes.
- [x] Focused workspace/ownership/navigation tests pass.
- [x] Existing six-primary-link UI test remains green.
- [x] Merge to main.
- [x] Sync Render deploy branch.
- [x] Deploy and verify new instance health.
- [x] Master plan updated with exact CI/PR/deploy evidence.

## Closeout

Status: DONE — the read-safe Sequence project workspace is implemented, tested and live.  
UI delivered: company-scoped sequence project list, empty-project creation, dedicated project workspace, canonical anchor timeline, lock/source state, clip and bridge status, candidate counts, selected version/model/generation state and a secondary status table.  
Navigation: Sekvenser is a Media sub-tab; the six primary desktop/mobile destinations remain unchanged and Media stays active on sequence pages.  
Safety: F1 exposes no regenerate, anchor-replace, provider-preview or paid-start action. Empty project creation performs no provider call. Company ownership is enforced by the existing workspace decorator plus project company lookup.  
Responsive/accessibility: native horizontal overflow on desktop, stacked vertical timeline on mobile, textual lock state, semantic timeline labels/roles and scrollable narrow status table.  
Migration: none. `makemigrations --check --dry-run` remained clean.  
CI: run `36000378816` passed full normal Django and PostgreSQL suites plus migration/check/static/MCP gates. Focused tests cover project creation, ownership, exact timeline order, lock state, version/status visibility, read-safe boundary, six-link primary navigation and responsive stylesheet behavior.  
PR: #58  
Main commit: `6a309fc1f461068eaa9a0e8f3bd1029994dc59c3`  
Deploy: `dep-daqhko3tqb8s73eh5rgg`; new instance `hkkd6` completed startup, returned `/healthz` 200 and Render marked the deploy `live`.  
Provider calls: none.  
Next exact task after F1: **F2 — Anchor controls.**
