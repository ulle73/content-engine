# ChatGPT Business → Content Engine MCP

This document defines the production integration between ChatGPT Business and the existing Content Engine.

## Architecture

```text
ChatGPT Business
      |
      | OAuth/OIDC bearer token + MCP Streamable HTTP
      v
content-engine-mcp (Render)
      |
      | authenticated Django user, company scoped
      v
Content Engine services + existing Django models
      |             |             |             |
      v             v             v             v
  OpenAI         Apify           R2           Postiz
      \______________ Neon/Postgres _____________/
```

Content Engine remains the system of record. ChatGPT is an operator interface. The MCP server does not keep a parallel content database and never returns provider credentials.

## Hard invariants

1. Every write is scoped from the authenticated identity to a `Company` owned by that Django user.
2. Every produced post lives in a real `ContentRun`; ideas, selected idea, copy, media and delivery remain attached to that run.
3. `record_predictions()` still runs before idea selection/publication. Existing production learning models can therefore influence idea ordering exactly as they do in Content Engine.
4. Postiz is never called directly by ChatGPT. Delivery always runs through `engine.delivery`, persists the external IDs on the same `ContentRun`, and preserves `OwnPost`/7–8 day outcome matching for ML.
5. External and paid writes use `OperatorAction` idempotency reservations. An uncertain provider result is never automatically replayed.
6. Run mutations use an optimistic `revision`. ChatGPT must read the latest run before overwriting copy/media/delivery state.
7. Postiz credentials, OpenAI keys, Apify tokens, R2 credentials and database credentials never appear in MCP tool output.
8. A ChatGPT-generated image is first ingested as a real company-scoped `MediaAsset`; Postiz delivery then uses that persisted asset.

## MCP endpoint

The MCP service exposes Streamable HTTP at:

```text
https://<content-engine-mcp-host>/mcp
```

Health check:

```text
https://<content-engine-mcp-host>/healthz
```

The service is intentionally deployed separately from the existing WSGI web service but uses the same codebase and the same production database.

## Authentication

Production uses an external OAuth/OIDC provider. The access token is validated against:

- `MCP_AUTH_ISSUER`
- `MCP_AUTH_AUDIENCE`
- optional `MCP_AUTH_JWKS_URL` (normally discovered from the issuer)
- optional `MCP_REQUIRED_SCOPE`
- `MCP_AUTH_USER_CLAIM`

The configured identity claim must uniquely match one active Django user's email or username. No company/user ID supplied by the language model can bypass that mapping.

For Microsoft Entra ID, a practical configuration is:

```text
MCP_AUTH_ISSUER=https://login.microsoftonline.com/<tenant-id>/v2.0
MCP_AUTH_AUDIENCE=<Application ID URI or API client id>
MCP_AUTH_USER_CLAIM=preferred_username
MCP_REQUIRED_SCOPE=content-engine.operate
```

The OAuth provider should issue refresh tokens/offline access for the ChatGPT connection. Register ChatGPT's callback/redirect URL in the OAuth client when ChatGPT shows it during custom-app setup.

`MCP_ALLOW_INSECURE_LOCAL`, `MCP_DEV_BEARER_TOKEN` and `MCP_DEV_USER_EMAIL` exist only for local/CI tests and must never be enabled on a public deployment.

## Render deployment

`render.yaml` adds a second service named `content-engine-mcp`.

The following values **must be identical to the existing `content-engine` service**:

- `DATABASE_URL`
- `POSTIZ_ENCRYPTION_SECRET`
- R2 credentials/bucket/endpoint
- provider credentials that the MCP should be allowed to use (OpenAI/Higgsfield)

`POSTIZ_ENCRYPTION_SECRET` is especially important: changing it makes existing encrypted Postiz credentials unreadable.

`SECRET_KEY` may technically differ, but using the same deployment secret is simplest. Never copy secrets into the repository.

The start command applies migrations and starts the ASGI MCP server:

```text
bash scripts/start-mcp.sh
```

## Tool model

### Read / state

- `list_companies`
- `get_company_context`
- `get_content_intelligence`
- `get_content_run`
- `list_media_options`
- `view_media`

### Intelligence / learning

- `refresh_content_engine`
- `refresh_published_performance`

These reuse the existing daily/performance/learning code and its existing Apify budgets, analysis caching and ML constraints.

### Content

- `create_content_run`
- `run_content_engine`
- `choose_idea`
- `rewrite_copy`
- `replace_copy`

`run_content_engine` is the high-level preparation tool. It can refresh due data, create the persisted run, select the top-ranked idea and create media options. It intentionally stops before external Postiz delivery so ChatGPT can inspect/select media and respect the user's delivery intent.

### Media

- `generate_media`
- `poll_media_generation`
- `save_chatgpt_image`
- `save_chatgpt_image_url`
- `select_media`

There are two supported image paths:

1. Content Engine generation → persisted `MediaGeneration`/`MediaAsset`.
2. ChatGPT native image generation → base64 or short-lived public HTTPS URL → validated ingest → persisted `MediaAsset` with ChatGPT provenance.

The URL ingest path uses the existing public-IP/HTTPS validation and refuses redirects/private network targets.

### Postiz

- `create_postiz_draft`
- `schedule_postiz`
- `publish_postiz_now`
- `reset_unknown_postiz_delivery`

They are intentionally separate MCP actions. Immediate publication must only be called for explicit user intent. Schedule uses Europe/Stockholm when a timezone is omitted and is normalized to UTC for Postiz.

If a run was first sent as a Postiz draft and the user later asks to schedule/publish it, Content Engine does **not** merely toggle the Postiz draft status because Postiz keeps the draft's stored date. Instead it creates the new scheduled/now object, atomically replaces the run's authoritative external IDs, and then best-effort removes the superseded non-public draft. This keeps later performance/ML mapping on the object that actually publishes.

## ML continuity

The MCP workflow preserves the existing learning chain:

```text
ContentRun
  → 3 grounded/ranked ideas
  → frozen Prediction rows
  → selected idea
  → persisted copy/media
  → Postiz IDs stored on the same ContentRun
  → OwnPost discovery
  → OwnSnapshot at current/final checkpoints
  → 7–8 day verified OwnOutcome
  → existing shadow/production learning pipeline
```

This means content created and delivered from ChatGPT remains eligible for the current ML implementation. The critical rule is that ChatGPT never bypasses Content Engine when sending to Postiz.

## Idempotency and uncertain writes

Every MCP mutation takes an `idempotency_key`. ChatGPT should:

- generate one key for one logical mutation;
- reuse the exact same key only when retrying the exact same mutation;
- generate a new key after changing the requested operation/payload;
- stop if Content Engine reports an uncertain external result.

Postiz/network timeouts after a POST are treated as uncertain because the remote service may already have accepted the write. The run moves to `unknown` and automatic replay is blocked. `reset_unknown_postiz_delivery` may only be used after a human/operator explicitly verifies that no corresponding Postiz object exists.

## ChatGPT Business setup

1. Deploy `content-engine-mcp` and apply the new migration.
2. Configure the OAuth/OIDC environment and verify `/healthz`.
3. In ChatGPT Business, enable Developer Mode as a workspace admin/owner.
4. Create a custom MCP app with `https://<host>/mcp`.
5. Select OAuth and finish authorization with the configured provider.
6. Scan tools and verify that the complete tool catalog is visible.
7. Test the app while it is still a draft.
8. Test one non-public flow end-to-end: create run → choose idea → generate/ingest image → select media → Postiz draft.
9. Test schedule on a controlled channel and confirm Postiz external IDs map back to the same `ContentRun`.
10. Only then publish the ChatGPT Business app to the workspace.

Because Business custom-app tool contracts may require recreation/republication to change after publishing, the full tool contract is implemented and CI-tested before the first workspace publication.

## Example operator flows

### "Kör Content Engine för Sänk Dig Golf och skapa det bästa inlägget för idag."

ChatGPT resolves the company, runs `run_content_engine`, inspects returned media with `view_media`, selects the strongest option with `select_media`, and returns the persisted result. It does not publish unless the user asked for delivery.

### "Ta idé 2 istället."

ChatGPT reads the current run, passes its latest revision to `choose_idea(idea_number=2)`, and continues on the same `ContentRun`.

### "Generera tre nya bilder här och använd bild 3."

ChatGPT generates images natively, saves each chosen candidate with `save_chatgpt_image`/`save_chatgpt_image_url`, visually inspects as needed, and calls `select_media` for the selected persisted asset.

### "Schemalägg på söndag 19:00."

ChatGPT resolves the concrete Stockholm date/time from the conversation and calls `schedule_postiz`. The same ContentRun keeps its Postiz external IDs so performance can later feed the existing ML pipeline.
