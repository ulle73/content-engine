# Product flow follow-up - 2026-09-30

## Scope and baseline

Repository: `ulle73/content-engine`. Branch: `codex/product-flow-integration`.

The starting commit was `03c30b7204563efb66f08c4fc0ae9ef7ed72262b`; main and the requested branch were identical at the initial comparison. The existing integration review, recent commits, Sequence/export and Motion/audio implementations were inspected and preserved. There is no root AGENTS.md in this snapshot. The vendor submodule's instructions were read; vendor code is unchanged.

Feature commit: `e373e2083aa5b50397bc046688139b5bff44f41d`.

No production deployment, production data mutation, paid provider generation, publishing, force-push, main update, new application dependency or database migration is part of this change.

## What changed

### Intent-first creation

Media opens the creation form ahead of the library. Image/video modes share the user's description. One image, portrait format, balanced priority and automatic model selection are the defaults. Alternative counts, priority and manual video model choice are under advanced settings. On small screens the AI form precedes upload.

Four beginner-facing video presets wrap existing trusted recipes: product reveal, place/environment, before/after and motion between two images. Preset selection never overwrites the user's idea. There is no parallel prompt/template engine.

### Start and end frames

Native, company-scoped image selectors have previews. Unavailable, expired, other-company assets and Motion previews are excluded. An older valid selected image remains selectable beyond the bounded 120-image list. Preset requirements are validated server-side.

The manual model list follows the existing verified request contracts and excludes incompatible end-image models. Auto remains recommended; final routing and preflight stay in the shared Creative Engine rather than browser code.

### Draft safety and recovery

The tab-local draft retains intent, frame choices and settings across image/video, animation and library-filter navigation. It is scoped to user/company/run, expires after two hours of inactivity, clears on logout and excludes credentials, CSRF and generation tokens. Explicit URL frame choices take precedence. Invalid POST and retry use authoritative server state.

Validation errors re-render the bound form without losing the idea. Retry restores the reviewed recipe, frames, format, priority and image count. Native forms still work without JavaScript; blocked browser storage produces an explicit fallback message.

### Existing engines remain connected

Explicit POST/CSRF-protected handoffs carry the edited visual intent to the existing Sequence or Motion screen using the same ContentRun. Company facts, original ideas and platform copy remain unchanged. Neither handoff starts a generation or creates an unexpected project.

Content Intelligence context is retained, not replaced with invented business data. This pass improves handoff of the brief; it does not introduce a new universal wizard or automatically transfer every frame/timeline setting between engines.

### Shared prompt compilation

The latest edited visual brief is now the default. The old video default invented multiple scenes and was rejected by the engine's own Sequence guard. Unspecified duration follows the chosen trusted recipe; explicit duration is retained. Camera intent no longer doubles as subject-motion permission, and an explicit static camera is not contradicted by recipe camera movement. Existing Sequence continuity strategies are preserved. Compiler version: `2026-09-30.1`.

## Verification

Candidate verification run **36785318278** completed successfully and published the feature commit above. The artifact `product-flow-candidate-evidence` contains logs, applied diff, screenshots, observations and `tested-commit.txt`.

| Check | Result |
| --- | --- |
| Initial regression baseline | 523 tests, OK; 3 PostgreSQL-only skips on SQLite |
| Expanded SQLite suite | 542 tests, OK; 3 PostgreSQL-only skips |
| Expanded PostgreSQL suite | 542 tests, OK; no skips, including locking/concurrency cases |
| Real Chromium suite | One end-to-end scenario; six groups of flow assertions, all passed |
| Responsive widths | 320, 390, 768 and 1440 px; no horizontal document overflow |
| Browser JavaScript errors / HTTP 5xx | None |
| Django system check / migration drift | Passed / no changes |
| New Python modules and browser script Ruff | Passed |
| JavaScript syntax / whitespace diff check | Passed |

Nineteen regression cases were added. Five initial new cases failed before the fixes. Changed legacy Python modules have the same ten existing lint findings as the baseline; a repository-wide lint cleanup is not claimed.

### What the browser actually did

Logged in through the real app; opened an image draft; typed a custom idea; clicked Animate; selected start/end frames and a preset; checked compatible models; switched image/video and library filters; submitted an invalid frame pairing and repaired it without losing text; opened a review using a synthetic read-only estimate; retried the reviewed choice; handed the edited brief to Sequence and then Motion; checked preservation of company facts and platform copy; captured responsive screenshots; submitted the native form by keyboard with JavaScript disabled; and opened the composer with sessionStorage blocked.

Paid start/upload entry points are guarded to fail if reached. Browser pricing is a synthetic USD 0.80 fixture, not a real quote. This verifies the review flow, not live provider quality or pricing.

### Test infrastructure and iteration

The pre-change Chromium run 36781331329 reproduced lost text after Animate and rejection of the app's own multi-scene default. During follow-up, shared in-memory SQLite connections produced intermittent authentication/asset failures in the live-server test. The browser suite now uses a temporary file-backed test database and independent connections. Application authentication and CSRF protections were not relaxed. Temporary authentication diagnostics were removed before the successful run.

Headless pointer-stability checks with JavaScript disabled were unreliable in this test environment. The final no-JavaScript check uses native keyboard submission instead; normal JavaScript-enabled flows use actual browser clicks. Screenshots of the composer, Sequence and Motion handoffs were visually inspected.

The temporary source-transfer workflow and compressed parts are removed by the documentation/cleanup commit. The retained `Product Flow Verify` workflow is read-only and repeats both database suites, static checks and real Chromium flows for future changes. It records its own tested commit in the artifact.

## Reproduce

```sh
python -m pip install -r requirements-dev.txt playwright==1.55.0
python -m playwright install --with-deps chromium
python manage.py test --settings=engine.test_settings --noinput
python manage.py check --settings=engine.test_settings
python manage.py makemigrations --check --dry-run --settings=engine.test_settings
python scripts/product_flow_browser.py
```

The browser script always uses test settings, temporary database/media directories and synthetic company data. The PostgreSQL workflow uses its own isolated service, not the production database.

## Still to do later

Validate real provider prices and output quality using an explicitly approved small budget. Run Safari/Firefox and physical-device checks before release. A fully guided cross-engine starting screen, richer thumbnail/upload controls and transfer of selected frames/timeline choices between engines remain useful next improvements.

No new complete Motion/Sequence render, live provider result, production deployment or export is claimed from this browser pass. Existing render/export coverage remains in the regression suite.
