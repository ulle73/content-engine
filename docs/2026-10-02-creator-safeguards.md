# Creator safeguards - 2026-10-02

Follow-up to [the combined creator](2026-10-01-combined-creator.md), on
`codex/product-flow-integration`. The server's default 2 USD ceiling is retained.

## Changes

- Planner and provider share the existing conservative Seedance 2.5 price
  rule and cost-ceiling parser in `engine/creative_budget.py`. No new price
  claims or provider calls are introduced by local planning.
- Auto preserves the requested duration, checks known local costs, and uses
  an affordable automatic resolution or skips a known over-budget model.
  The 8-second premium reveal uses 480p: the existing rule computes 1.6448 USD.
  A visible preview warning explains this resolution choice. With a 4 USD
  ceiling the same Auto plan retains 720p.
- Explicit resolution/model choices are preserved. Known over-budget choices
  fail before job creation or provider I/O, with an actionable error. A long
  request is not shortened to evade the budget.
- Models without a local price rule still require authenticated provider
  estimation; a local plan never guarantees their final price. The existing
  provider cost guard remains authoritative, including when an old job's
  budget is lowered or descriptive pricing changes.
- Explicit Swedish/English subject movement versus stationary-subject choices
  are validated before compilation. The reproduced `Bollen lyfter` plus
  `Vara stilla` conflict fails with the original text and selections retained.
  Camera/environment movement, negations, and the Follow my idea choice have
  separate regression coverage. This is bounded deterministic detection,
  not a general natural-language consistency guarantee.
- Capability-only tests use explicit ample test budgets; production/default
  budget behavior has separate regression coverage. Both CI lint commands
  include the shared budget module.

## Verification

- SQLite full suite: 576 tests, OK, 3 PostgreSQL-only skips.
- PostgreSQL full suite: 576 tests, OK, no skips. The same test command used
  by Product Flow Verify ran locally against an isolated PostgreSQL 17.11
  cluster bound to 127.0.0.1:55439. No production database was used. The
  temporary server was stopped after testing.
- Product-flow Chromium harness: 8 check groups, OK, no JavaScript errors,
  including the actual budget-warning display and motion-conflict repair.
- Creator Chromium harness: picker/search/pagination/upload/swap, preview,
  retries, workflow handoffs and 56 route/width checks, OK.
- Targeted Ruff, JavaScript syntax, Django check, migration drift and Git
  whitespace checks passed. No product dependency or migration was added.

Ignored local evidence: `data/creator-fixes-sqlite.log`,
`data/creator-fixes-postgres.log`, `data/creator-fixes-product-browser.log`,
`data/creator-fixes-creator-browser.log`, `data/product-flow-browser/combined/`
and `data/creator-browser/`.

Test-only PostgreSQL runtime was obtained from the official
[EDB binary download page](https://www.enterprisedb.com/download-postgresql-binaries)
and retained under ignored `data/test-tools/postgres-17/`.

## Remaining boundaries

These are local results, not a GitHub-hosted CI run or production acceptance.
No push, main update, deployment, paid generation, publication, or production
data changes were performed. Live provider output, storage/OAuth and physical
devices remain unverified. The previously noted unbounded native image-option
rendering remains a separate large-library performance risk.
