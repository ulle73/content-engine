# Intent-first creation: implementation and acceptance

## Scope and source

Work continues on the explicitly requested branch `codex/product-flow-integratio` (exact spelling), based on `main` at `03c30b7204563efb66f08c4fc0ae9ef7ed72262b`. Main and production were not changed. The code version verified below is `9edba996675ea162849a96037348770255320144`; this report adds documentation only.

The existing CreativeBrief, model registry, creative recipes, MediaGeneration/MediaAsset, ContentRun, Motion and Sequence services are reused. No new database models, migrations or production dependencies were introduced. There was no root AGENTS.md in the checked-out base. Existing architecture, creative intelligence, model audit and Motion/Sequence documentation were inspected.

## Problems fixed

- Creation was below the media browser and often started with an invented technical four-scene brief rather than the user's idea.
- Selecting images, changing creation type and retrying could discard an unfinished idea or chosen options.
- Existing structured recipes were not available as simple choices in the creation flow.
- Auto could round an eight-second request to ten seconds even when another verified, compatible model supported eight.
- User camera instructions could be overshadowed by generic recipe defaults.
- Moving to Motion or Sequence required extra copying and did not consistently carry selected images.
- Motion detected a monthly summary but did not prefill the explicit numbers from the same idea.
- A real-browser test exposed quiet-button specificity and smooth-scroll races: workflow handoff targets became about 15 pixels high and could move during a click. Scoped 44-pixel targets and stable editor navigation fixed the actual failing interaction.

## How creation works

1. Open **Skapa video** or **Skapa bild**. The editor is first; finished-media browsing and upload are secondary disclosures.
2. Choose start/end images in place, search the same company library, load more images, or upload a new image without navigating away. Replace, remove and swap are explicit actions.
3. Describe what should happen in normal words. An optional familiar template and format/duration are the primary choices. Camera, subject motion and ending are optional; technical controls remain under Advanced.
4. A local, non-billable preflight compiles a model-specific instruction with the existing engine. The original idea is not replaced. Changing a model or reference recompiles the preview. The compiled prompt is available under **Visa AI-instruktion**.
5. **Granska före start** prepares the existing review flow. Price review and explicit paid start remain separate; local preview never starts paid generation.
6. **Text och siffror** opens Motion; **Film av flera delar** opens Sequence. The idea, format and validated images follow. The existing single-film/Media output paths remain in place.

Session recovery is scoped to user, company and ContentRun in the current browser tab. It is not a promise of cross-device cloud autosave. Server-side handoff preserves existing copy and increments the run revision under a lock. Delivered runs and foreign/expired/unpublishable references are rejected.

## Model intelligence and templates

The six user-facing video template labels point to existing structured recipes: Filmisk reveal, Produkt i fokus, Före och efter, Mjuk övergång, Golfbana och miljö, and Lugn varumärkesfilm. They are not a second prompt library or static prompt strings.

`creative_controls.py` maps human choices to validated CreativeBrief fields. Existing model request contracts determine modes, reference roles, duration, aspect behavior, resolution and audio support. Auto first preserves exact requested duration among compatible verified candidates and then applies the existing priority ranking. Manual model selection remains strict. Contradictory explicit duration, resolution, audio and static/moving camera instructions produce an actionable error instead of a silent rewrite.

The shared compiler also accepts controls and recipe selection through MCP `preview_media`; authentication, ownership, revision checks, idempotency and explicit-start protection remain. The browser's immediate local preflight does not upload references; MCP/server cost review may upload a reference for a provider estimate, as before.

Motion fills explicitly supplied monthly counts, currency totals and month. Missing areas are left blank, not invented. Templates that do not consume selected images say so. Sequence receives the selected images in order through its existing anchor/project services, without starting generation.

## Executed acceptance

| Gate | State | Direct evidence |
| --- | --- | --- |
| Django suite on SQLite | PASS | 547 tests, OK, three PostgreSQL-specific tests skipped; local and isolated Linux CI. |
| Django suite on PostgreSQL | PASS | 547 tests, OK, no skips, 29.414 seconds; Content Engine MCP Verify run `36781226906`, job `110111695118`. |
| Django checks and migration checks | PASS | System checks, fresh migrate, migrate --check and makemigrations --check --dry-run succeeded in MCP CI. No new migrations. |
| MCP startup and shared behavior | PASS | Existing scoped-operation, authentication/revision/safety tests plus ASGI startup and MCP-settings checks passed in the full suite/workflow. This is not a live ChatGPT OAuth test. |
| New Python lint and JavaScript syntax | PASS | Ruff for new creator modules/harness, node --check and git diff --check passed. |
| Real browser interactions | PASS | Creator acceptance run `36781226765`, artifact `11128720035`: image search, pagination beyond 60 items, real multipart upload, swap, capability filtering, model recompilation, reload, image/video switching, review, cancel, retry, Sequence creation with ordered images, and Motion creation with explicit numbers. Zero paid provider starts. |
| Responsive pages | PASS | Same Chromium run: 14 routes at 320, 390, 767 and 1440 CSS pixels; all 56 returned HTTP 200, no horizontal document overflow, no page JavaScript errors. Screenshots were inspected for changed desktop/mobile views. These are viewport checks, not physical-device Safari certification. |
| Remotion tests, types and bundle | PASS | Motion Engine CI run `36781226724`, job `110111694886`. |
| Actual Motion render and decode | PASS | Four outputs passed the real ingestion quality validator and full FFmpeg decode; artifact `11128510613`. See below. |
| Paid provider output quality | NOT RUN | No paid image/video generation or visual A/B comparison was performed. Better prompt structure/routing is verified; empirically better generated output is not claimed. |
| Production end-to-end acceptance | NOT RUN | No deployment, production DB/R2 mutation, external OAuth session or Postiz delivery/publication. Existing approval safeguards remain. |

The real browser ran against an isolated instance of the actual Django app with temporary SQLite, local media and clearly synthetic Golfkuponger data. The working container could not launch a permitted browser session, so the browser was run in GitHub Actions; this was not replaced by a static HTML mockup. No production credentials were used.

### Render evidence

All four outputs contain 538 frames at 30 fps, H.264 video in yuv420p/BT.709 and AAC audio. The decoder and ingestion checks verified non-silent audio without clipping.

| Output | Dimensions | Render seconds | Peak RSS MB |
| --- | --- | --- | --- |
| Preview 9:16 | 360 x 640 | 37.81 | 689.5 |
| Final 9:16 | 1080 x 1920 | 50.65 | 809.2 |
| Final 1:1 | 1080 x 1080 | 42.59 | 670.1 |
| Final 16:9 | 1920 x 1080 | 50.71 | 803.3 |

These are the representative synthetic Monthly Wrapped smoke outputs, not paid AI outputs or production-company videos.

## Reproduction

Run in a clean isolated environment, never against production:

```sh
python manage.py test --settings=engine.test_settings --noinput
python manage.py check --settings=engine.test_settings
python manage.py makemigrations --check --dry-run --settings=engine.test_settings
ruff check engine/creative_controls.py engine/test_creator.py scripts/creator_browser_smoke.py
node --check engine/static/js/creator.js
# Requires Playwright and its Chromium installation for test execution only:
python scripts/creator_browser_smoke.py
# With an isolated TEST_DATABASE_URL:
python manage.py test engine operator_bridge --settings=engine.postgres_test_settings
# In motion-renderer:
npm test
npm run typecheck
npm run build
# From repository root, with FFmpeg/FFprobe:
python scripts/motion_render_smoke.py
```

`creator-verify.yml` preserves the interactive browser check on this branch and pull requests to main. Browser screenshots, trace and JSON acceptance are stored in `data/creator-browser`; CI uploads them as artifacts with bounded retention. One-time source-transfer workflows were removed after use.

## Remaining release/quality work

The implementation and isolated acceptance above are complete, but this is not a claim that every broad product ambition has been empirically fulfilled. Before a production rollout, use an explicitly approved small generation budget to review real product/logo fidelity, start/end continuity and model-specific output quality. Test the deployed browser-to-provider-to-R2-to-Media path and public OAuth connection. Broader template examples, more natural-language ambiguity handling and physical-device accessibility/usability testing remain reasonable improvements. No automatic deployment or publication is configured by this change.
