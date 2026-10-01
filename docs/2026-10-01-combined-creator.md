# Combined creator implementation - 2026-10-01

## Result

The richer creator from `codex/product-flow-integratio` is integrated into
`codex/product-flow-integration`, preserving both histories and the latter's
planner and draft-safety corrections. There is one creation form and compiler.
The retired composer module, template, stylesheet and script are removed.

Merge parents:

- Main working branch: `3870bfca84445e0231e0c9d24982893fd33bdaf0`.
- Rich creator source: `dc57b4316a5205e0a610cee20b96f9ace7b52f04`.
- Comparison baseline: `origin/main` at `03c30b7204563efb66f08c4fc0ae9ef7ed72262b`.

## Behavior

- Creation opens before the existing media library, including the default page.
- Start/end image selection supports thumbnails, search, pagination, inline
  upload, replacement, removal and swapping without losing the user's text.
- Recipe, camera, subject movement, ending, duration, audio, resolution and
  model controls compile through the existing verified registries. Local live
  previews have no provider call or generation-row side effect.
- Auto favors a compatible model supporting the requested duration exactly.
- The newest saved visual brief is used for both image and video; no default
  multi-scene script is invented. Unspecified duration follows the recipe.
- Explicit static camera instructions are preserved, and camera movement does
  not grant permission to change the subject. Recipe continuity is retained.
- Drafts are scoped to user/company/run, expire after two hours of inactivity,
  and keep video-specific settings separate from image settings. Bound errors,
  retries, explicit frame URLs and changed server briefs take precedence.
- Logout clears creator drafts from every page. Blocked storage is reported;
  the native form remains usable with JavaScript disabled.
- Sequence/Motion handoffs preserve the edited brief and selected images,
  format, company facts and platform copy. Handoff updates the existing
  operator revision. The old handoff URL remains an alias of the shared action.
- Retry restores recipe and shape from older jobs lacking creator metadata.

## Verification

- Final SQLite regression suite: 568 tests, OK; three PostgreSQL-only skips.
- Both browser harnesses passed with isolated synthetic data and local media.
- Creator harness: real search/pagination/upload/swap/model/preview/retry and
  Sequence/Motion project interactions; 56 route/width checks at
  320/390/767/1440 px; HTTP 200, no horizontal overflow or JavaScript errors.
- Product-flow harness: Animate/filter/kind recovery, separate video settings,
  static camera preview, invalid-submit repair, synthetic price review/retry,
  two-hour expiry, scoped token-free storage, ordered image handoff, server
  baseline precedence, native keyboard submission, blocked storage and logout
  from Sequence. Responsive checks at 320/390/768/1440 px passed.
- Creator desktop/mobile and initial image-editor screenshots were reviewed.
- Django checks, migration drift, targeted Ruff, JavaScript syntax and Git
  whitespace/conflict checks passed. No new migration or product dependency.

Local evidence (ignored): `data/combined-full-tests.log`,
`data/combined-product-browser.log`, `data/creator-browser/acceptance.json`,
`data/product-flow-browser/combined/observations.json` and accompanying PNGs.
Windows browser harnesses explicitly close SQLite connections before cleanup.
FFmpeg was provided only in the ignored test-tools directory for worker tests.

Reproduce with the existing virtual environment, Playwright Chromium and
FFmpeg on PATH:

```powershell
python manage.py test --settings=engine.test_settings --noinput
python manage.py check --settings=engine.test_settings
python manage.py makemigrations --check --dry-run --settings=engine.test_settings
python scripts/product_flow_browser.py
python scripts/creator_browser_smoke.py
```

## Boundaries

No push, main update, deployment, real paid generation, production-database
change or publication was performed. PostgreSQL was not available locally;
the retained Product Flow Verify workflow runs its isolated PostgreSQL suite
when the branch is pushed or a PR is opened. Live provider prices/output,
external storage/OAuth, Safari/Firefox and physical-device release acceptance
remain unverified. Earlier CI results from either parent do not prove this
combined commit's PostgreSQL or production behavior.
