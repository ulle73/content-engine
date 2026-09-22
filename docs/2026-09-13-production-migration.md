# Production migration, 2026-09-13

## Result and live addresses

The existing Content Engine data was migrated to the owner's Neon project. The
existing editor, self-hosted OAuth and 22 MCP tools share the Render service:

- Editor: https://content-engine-mcp.onrender.com/
- MCP: https://content-engine-mcp.onrender.com/mcp
- Database readiness: https://content-engine-mcp.onrender.com/healthz
- Render service: `srv-daj9cfgae00c7392t5c0`, Frankfurt, workspace
  `tea-d06041ali9vc73bqfn80` (explicitly confirmed by the owner).
- Git deployment branch: `feature/chatgpt-content-engine-mcp` only.
- `main` and `origin/main` remain at `e92f85b9317ba7e9ac40baf990e01072c8073c8e`.

## Previous operation and migration reason

The app had been run locally using `start.ps1` / Waitress on port 8765. Its
database was already PostgreSQL 17.11 on Neon, not a local SQLite file:

`ep-flat-dawn-b12oghtp.c-5.eu-central-1.aws.neon.tech`, database `content_engine_app`.

The local `.env` and the existing GitHub `CONTENT_DATABASE_URL` secret matched.
The existing GitHub Daily workflow was enabled and its successful September 13
run was verified (`34755538248`). No old Content Engine Render web service was
found in the confirmed workspace; `content-engine-mcp` was a newly created
service initially connected to empty application tables.

The old Neon project was absent from the accessible organizations/projects, and
the owner did not know which account created it. Moving to the verified account
therefore establishes administrative control; it is not a PostgreSQL upgrade or
a demonstrated storage-capacity increase.

Target: project `orange-band-72152493`, branch `br-frosty-boat-b1zvyemp`, database
`content_engine_app`, PostgreSQL 17.11, Frankfurt. At verification it had a
512 MiB branch limit and six-hour history retention on Free. The old database
occupied about 12 MB; its plan/limit/ownership remain unverified. Media are in R2.

## Preserved data

The transfer used a read-only REPEATABLE READ snapshot. It preserved primary
keys, foreign keys, JSON, decimals, ciphertext, passwords and full microsecond
timestamps. Default Django JSON encoding would truncate timestamps; the migration
uses `ExactJSONEncoder` instead. Source user/group relations use natural foreign
keys so Django's newly generated content-type/permission metadata can coexist.

Every source application, auth and session table matched by row count and
SHA-256 over canonical complete PostgreSQL rows, before production use resumed.
Django-generated permission/content-type/migration metadata are intentionally
not overwritten. Import validates source migrations and deferred foreign keys,
refuses an occupied application database, and rolls back on any mismatch.
Unrelated target table `playing_with_neon` was preserved unchanged.

| Source data | Rows |
|---|---:|
| Users / companies / ContentRuns | 1 / 3 / 4 |
| ContentEvents / Predictions | 16 / 3 |
| MediaAssets / MediaGenerations | 4 / 4 |
| Competitors / imports / posts / snapshots | 5 / 32 / 414 / 665 |
| AdAccounts / ads / observations | 4 / 15 / 43 |
| AnalysisMemos | 10 |
| ScraperStates / ScrapeRequests | 10 / 25 |
| DailyRuns / DailySteps | 5 / 276 |
| OwnPosts / OwnSnapshots | 1 / 4 |
| LearningModels / OwnOutcomes | 0 / 0 |

There were no trained model artifacts or measured training outcomes to transfer.
The real frozen predictions, events, observations and performance history were
preserved; no historical labels or models were invented.

All four original R2 objects were downloaded and matched their stored byte sizes.
Their historical `sha256` fields were blank; no claim of comparison against a
previous stored content hash is made. Existing storage keys were unchanged.

Rehearsal passed on isolated Neon branch `br-ancient-night-b1bt2fuu`
(`migration-rehearsal-20260913`). The production import then passed the same
comparison. GitHub Daily was briefly disabled for snapshot/cutover, its database
secret was switched, then the original activation flag was restored to `true`.
The local `.env` was switched after retaining its original privately.

## Credentials and integrations

| Configuration | Migration / verification |
|---|---|
| `DATABASE_URL` | New Neon, shared by Render, local app and GitHub Daily |
| `DATABASE_URL_UNPOOLED` | Direct target URL for migrations on Render |
| `SECRET_KEY` | Original value preserved |
| `POSTIZ_ENCRYPTION_SECRET` | Explicitly set to original value; original local fallback was `SECRET_KEY`, matching GitHub |
| Postiz | Existing company ciphertext decrypted; both stored channels verified with live GET |
| `OPENAI_API_KEY` | Existing GitHub credential transferred; live text and image generation passed on Render |
| `APIFY_API_TOKEN` | Existing credential transferred; authenticated `/v2/users/me` returned 200 |
| R2 endpoint, bucket, access key, secret, region | Existing `content-engine-media` bucket retained; live image read/write and preview passed |
| Higgsfield key/secret | Transferred; live estimate accepted (10-second text-to-video: USD 0.700) |
| Budget controls | USD 1/day/company scraping, 12 analyses/day/company, USD 2/video ceiling retained |
| Development bearer authentication | Explicitly disabled on Render; public settings now reject enabling it |

An ephemeral branch-restricted GitHub workflow exported existing secrets as an
RSA-OAEP/AES-GCM encrypted artifact. Its private key stayed in the local private
migration directory. Plaintext secrets were not written into Git, logs or GitHub
artifacts. The handoff workflow and public key were removed after use.
The old `.env`'s `POSTIZ_API_KEY`, `ENCRYPTION_KEY_SALT`, `ALLOWED_HOSTS` and
`EMAIL_BACKEND_TYPE` are legacy values not consumed by the current integration;
the company-scoped encrypted Postiz records remain authoritative.

## Runtime fixes and tests

- Migrations use a direct Neon connection before taking a bounded session advisory
  lock; transaction pooling cannot safely hold that lock.
- PostgreSQL connections have health checks and a connection timeout. ASGI disables
  persistent connections, and each MCP worker tool closes its own connections.
- PostgreSQL row locks in idea selection/delivery lock the ContentRun itself,
  avoiding `FOR UPDATE` on the nullable media outer join.
- `/healthz` queries the database and returns 503 without error details when unavailable.
- OAuth/login templates now have the existing dashboard routes; the whole editor
  is served on the MCP origin without provisioning another service.
- CI runs the suite on isolated SQLite and PostgreSQL 17, with Python 3.13.
  Workflow `34759334081` passed both jobs (106 tests each). Local Windows Python
  3.14 also passed all 106 tests after dependencies finished initializing.
- Schema drift check: no missing model migrations.

Live OAuth verification used a temporary isolated test user: normal password login,
consent, S256 PKCE, authorization-code exchange and refresh-token rotation passed.
That user's MCP company list was empty, as required. Existing-owner operations
used an explicitly scoped, short-lived administrative verification token; the
owner's password and pre-existing authorizations were not changed. Temporary QA
credentials are revoked after validation. The owner's interactive ChatGPT setup
is a separate manual final step, not claimed as tested here.

Daily run `34759115604` on the feature branch succeeded against the new database:
same preserved daily UUID `cd829b41-fdd3-4bb6-9afe-890c5e5b566d`, 41 skipped and
10 successful steps, zero attention. This demonstrates continuity/idempotency;
it is not evidence of a newly launched paid scraper run.

## Real non-public end-to-end verification

ContentRun `a18ef15c-f040-438c-8b51-cbc5642d16cf` belongs to the existing Sänk Dig
company. Through the public Render MCP endpoint it received three real grounded
ideas and frozen predictions, selection and platform copy, and one OpenAI image.

Image `497e5fb5-4d25-52f9-aaa3-7e13359033fa` is persisted in R2, 2,434,445 bytes,
SHA-256 `747077fad7bddc4192fa76630eedd82e7de7751fa2313ed39f616d98d09a88be`.
It was retrieved through `view_media`, visually inspected and selected on the run.

The copy was explicitly prefixed `MIGRERINGSTEST 2026-09-13 - EJ FOR PUBLICERING`.
Postiz returned two posts, independently reread as `DRAFT` with empty `releaseId`:

- `cmu04a47p02q0lm0ynquan9g4`
- `cmu04a49e02q1lm0yq2qmxykg`

Both match the same ContentRun through the existing performance/ML matching code.
Predictions precede selection; no outcome was fabricated. Repeating create-run,
idea selection and delivery with the same idempotency keys created no duplicate
runs or drafts. One client connection broke after selection; fresh state showed
the completed selection and the same-key retry safely returned it.

Nothing was scheduled or published. Live video generation was not run: this task
verified Higgsfield authentication/estimate, not available credits or finished
video. The prior implementation documented insufficient API credits.

## Backups and rollback

Private local checkpoint directory:
`C:\dev\content-engine\data\migration-20260913` (Git-ignored, Windows ACL restricted
to the current user). It contains the source `.env`, cutover fixture/manifest,
checksums and validation reports. Never commit or share its credential files.

An independently downloaded and decrypted backup is in the existing private R2
bucket at `backups/migration-20260913/content-engine-pre-cutover.tar.gz.aesgcm`.
Ciphertext SHA-256:
`8b4ff061453e944c9d94f7e653c126c72cde07f58e82dd3cd49c9e6fd23d6ead`.
Its payload is a gzip tar of `data.json` and `manifest.json`.

Encryption format: 12-byte nonce followed by AES-256-GCM ciphertext/tag. Derive
the key from the original `POSTIZ_ENCRYPTION_SECRET` using HKDF-SHA256, length 32,
salt `content-engine-backup-v1`, info `migration-20260913`. Additional authenticated
data is `content-engine-migration-20260913`. Keep that secret backed up separately.

Pre-import Neon snapshot: `snap-wispy-bar-b17qfb96`. The old source database and
the rehearsal branch also remain available. They are not an ongoing backup of
new production writes.

For rollback, first stop all current writers and back up new production data.
Do not simply point clients back to the old database: it lacks records created
since cutover. Restore the checkpoint to an empty migrated database with
`python scripts/migrate_data.py restore <checkpoint-directory>`, using a direct
`DATABASE_URL`; preserve/reconcile all subsequent records before switching.
`verify` checks complete source rows; it deliberately fails after intentional
changes/new rows, so use the saved cutover evidence plus primary-key comparisons
for later preservation audits. Unknown non-app source tables cause snapshot to
fail closed and require an explicit mapping before a future full migration.

## Remaining operator choices / access

1. The live Render plan is Free. It sleeps after inactivity; a real sleep/wakeup
   occurred during this session. Starter is recommended for always-on service
   (listed at about USD 7/month), but no paid upgrade was approved or performed.
2. Set the existing Render service's **Health Check Path** to `/healthz`. It is in
   `render.yaml` but the API-created service still had an empty field. The installed
   Render connector cannot edit this field, and the browser is not signed into
   Render. The endpoint itself is tested and database-aware.
3. In ChatGPT Business, add the custom OAuth MCP app at the URL above and sign in
   with the existing Content Engine account. This user's interactive consent and
   workspace installation cannot be completed without their authenticated session.
4. Faiv and Golfkuponger exist but do not yet have complete current company facts
   or Postiz connections. These were already absent in the source. Sänk Dig's
   existing configured flow is verified.

For longer-term operations, choose an ongoing encrypted backup schedule and
appropriate Neon retention/plan. The verified R2 checkpoint protects this migration;
it is not a claim that ongoing backup coverage has already been configured.
