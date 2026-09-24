# Sequence Workspace F1 — Project Workspace Ledger

**Date:** 2026-09-24  
**Status:** ACTIVE until all release gates pass.  
**Depends on:** E1–E4 live Sequence Engine backend.

> F1 is a thin UI/read model over verified sequence services. It may create an empty SequenceProject, but it must not mutate anchors/clips/bridges or start provider generation.

## F1.1 Navigation and project list

- [ ] Keep the six primary app destinations unchanged.
- [ ] Add Sekvenser as a sub-tab under Media.
- [ ] Sequence pages keep Media highlighted in desktop/mobile navigation.
- [ ] Company-scoped project list shows status and anchor/clip/bridge counts.
- [ ] Empty state explains what comes next.
- [ ] User can create an empty company-scoped SequenceProject.
- [ ] Project creation validates title, format, platform and bounded brief.
- [ ] Creating a project performs no provider call.

## F1.2 Dedicated project workspace

- [ ] Dedicated project URL scoped to the owning company.
- [ ] Project header shows status, format and platform.
- [ ] Summary shows anchor, clip, bridge and candidate counts.
- [ ] Timeline shows canonical anchor order.
- [ ] Anchor card shows thumbnail, K-position, locked/unlocked state and source provenance.
- [ ] Clip cards show status, recipe, candidate count and selected version/model.
- [ ] Bridge cards are visually distinct and show source clip pair.
- [ ] Segment status table shows selected generation status.
- [ ] Empty projects render safely.

## F1.3 Safety boundary

- [ ] No regenerate action.
- [ ] No anchor replace action.
- [ ] No provider preview/start action.
- [ ] No paid generation action.
- [ ] No sequence domain rule is duplicated in template code.
- [ ] Cross-company project lookup returns 404.
- [ ] Existing E1–E4 services/models remain source of truth.

## F1.4 Responsive/accessibility baseline

- [ ] Desktop timeline uses native horizontal overflow rather than custom carousel JS.
- [ ] Mobile timeline stacks vertically.
- [ ] Lock state is text, not color-only.
- [ ] Timeline has semantic labels/roles.
- [ ] Status table remains scrollable on narrow screens.
- [ ] Native details/summary used for project-create disclosure.

## Release gates

- [ ] No migration required.
- [ ] `makemigrations --check --dry-run` passes.
- [ ] Full normal Django suite passes.
- [ ] Full PostgreSQL suite passes.
- [ ] Focused workspace/ownership/navigation tests pass.
- [ ] Existing six-primary-link UI test remains green.
- [ ] Merge to main.
- [ ] Sync Render deploy branch.
- [ ] Deploy and verify new instance health.
- [ ] Master plan updated with exact CI/PR/deploy evidence.

## Closeout

Status: NOT STARTED  
CI: —  
PR: —  
Main commit: —  
Deploy: —  
Provider calls: none.  
Next exact task after F1: **F2 — Anchor controls.**
