# ChatGPT Business → Content Engine MCP

This document defines the production integration between ChatGPT Business and the existing Content Engine.

## Architecture

```text
ChatGPT Business
      |
      | OAuth 2.1 + MCP Streamable HTTP
      v
content-engine-mcp (Render)
      |
      | same Django users + same database
      v
Content Engine services + existing Django models
      |             |             |             |
      v             v             v             v
  OpenAI         Apify           R2           Postiz
      \______________ Neon/Postgres _____________/
```

Content Engine remains the system of record. ChatGPT is an operator interface. The MCP server does not keep a parallel content database and never returns provider credentials.

## Hard invariants

1. Every write is scoped from the authenticated Content Engine user to a `Company` owned by that user.
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

The production service hosts the existing Django editor, OAuth and MCP on one Render origin, using one production database. The WSGI entrypoint remains available for local/alternative deployments.

## Authentication — no Microsoft/Entra or external IdP

`content-engine-mcp` is its own OAuth authorization server. It uses Django OAuth Toolkit 3.4.x and the **existing Content Engine Django users**.

The user experience is:

```text
ChatGPT → Content Engine OAuth login → normal Content Engine email/password → consent → MCP access
```

There is no Microsoft Entra app registration, no Google/Auth0 dependency and no separate identity database.

Security posture:

- Authorization Code flow only.
- S256 PKCE required.
- Refresh-token rotation and reuse protection.
- Access token lifetime: 1 hour.
- Refresh token lifetime: 90 days.
- Access/refresh tokens are hashed at rest.
- OAuth `resource` is bound to the exact MCP URL (`https://<host>/mcp`).
- The MCP resource server rejects tokens without `content-engine.operate`.
- The bearer token maps directly to the Django user ID that authorized it; user/company IDs supplied by the language model cannot elevate access.
- Dynamic Client Registration exists only as an MCP compatibility fallback and accepts only explicit HTTPS ChatGPT/OpenAI callback hosts.
- Client ID Metadata Documents are enabled for modern MCP clients.

OAuth/authorization-server metadata is exposed on the same MCP host under the standard well-known routes. ChatGPT can therefore discover authorization/token/registration endpoints from the MCP endpoint without manually configuring an external issuer.

Local-only development variables (`MCP_ALLOW_INSECURE_LOCAL`, `MCP_DEV_BEARER_TOKEN`, `MCP_DEV_USER_EMAIL`) must never be enabled on the public deployment.

## Render deployment

`render.yaml` describes the combined service named `content-engine-mcp`, pinned to `feature/chatgpt-content-engine-mcp`. The production editor is at `https://content-engine-mcp.onrender.com/` and the MCP endpoint is `/mcp`.

The following values must point at the same Content Engine system of record/providers as the existing service:

- `DATABASE_URL`
- `POSTIZ_ENCRYPTION_SECRET`
- R2 credentials/bucket/endpoint
- OpenAI key
- Apify token where intelligence refresh should be available
- Higgsfield credentials where video generation should be available

`POSTIZ_ENCRYPTION_SECRET` must be exactly the same value as the existing `content-engine` service or existing encrypted Postiz credentials cannot be decrypted.

The migration preserves the existing Django `SECRET_KEY` and the exact Postiz encryption secret. Neither should be regenerated during deployment. Microsoft or any external OAuth secret is unnecessary.

The start command applies migrations with the shared migration lock and starts the combined MCP/OAuth ASGI service:

```text
bash scripts/start-mcp.sh
```

`RENDER_EXTERNAL_URL` automatically becomes both the OAuth issuer and the base for the protected MCP resource. No `MCP_AUTH_ISSUER`, `MCP_AUTH_AUDIENCE` or JWKS configuration is required.

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

The URL ingest path uses HTTPS/public-IP validation and refuses redirects/private-network targets.

### Postiz

- `create_postiz_draft`
- `schedule_postiz`
- `publish_postiz_now`
- `reset_unknown_postiz_delivery`

They are intentionally separate MCP actions. Immediate publication must only be called for explicit user intent. Schedule uses Europe/Stockholm when a timezone is omitted and is normalized to UTC for Postiz.

If a run was first sent as a Postiz draft and the user later asks to schedule/publish it, Content Engine does not merely toggle the Postiz draft status because Postiz keeps the draft's stored date. Instead it creates the new scheduled/now object, replaces the run's authoritative external IDs, and then best-effort removes the superseded non-public draft. This keeps later performance/ML mapping on the object that actually publishes.

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

Content created and delivered from ChatGPT therefore remains eligible for the current ML implementation. The critical rule is that ChatGPT never bypasses Content Engine when sending to Postiz.

## Idempotency and uncertain writes

Every MCP mutation takes an `idempotency_key`. ChatGPT should:

- generate one key for one logical mutation;
- reuse the exact same key only when retrying the exact same mutation;
- generate a new key after changing the requested operation/payload;
- stop if Content Engine reports an uncertain external result.

Postiz/network timeouts after a POST are treated as uncertain because the remote service may already have accepted the write. The run moves to `unknown` and automatic replay is blocked. `reset_unknown_postiz_delivery` may only be used after a human/operator explicitly verifies that no corresponding Postiz object exists.

## ChatGPT Business setup

1. Deploy the `content-engine-mcp` Render service from the tested branch/merged commit.
2. Give it the shared `DATABASE_URL`, `POSTIZ_ENCRYPTION_SECRET`, R2/provider credentials and verify `/healthz`.
3. Open `https://<mcp-host>/.well-known/oauth-authorization-server` and verify OAuth discovery returns the MCP host as issuer.
4. In ChatGPT Business, enable Developer Mode as a workspace admin/owner.
5. Create a custom MCP app with `https://<mcp-host>/mcp`.
6. Choose OAuth when prompted. ChatGPT discovers the Content Engine OAuth server itself.
7. Sign in with the normal Content Engine account and approve the requested `content-engine.operate` access.
8. Scan tools and verify the complete tool catalog is visible.
9. Keep the app as a draft while testing one non-public flow end-to-end: create run → choose idea → generate/ingest image → select media → Postiz draft.
10. Test schedule on a controlled channel and confirm Postiz external IDs map back to the same `ContentRun`.
11. Only then publish the ChatGPT Business app to the workspace.

No Microsoft Entra configuration, external OAuth client secret or third-party identity service is part of this setup.

## Example operator flows

### "Kör Content Engine för Sänk Dig Golf och skapa det bästa inlägget för idag."

ChatGPT resolves the company, runs `run_content_engine`, inspects returned media with `view_media`, selects the strongest option with `select_media`, and returns the persisted result. It does not publish unless the user asked for delivery.

### "Ta idé 2 istället."

ChatGPT reads the current run, passes its latest revision to `choose_idea(idea_number=2)`, and continues on the same `ContentRun`.

### "Generera tre nya bilder här och använd bild 3."

ChatGPT generates images natively, saves each chosen candidate with `save_chatgpt_image`/`save_chatgpt_image_url`, visually inspects as needed, and calls `select_media` for the selected persisted asset.

### "Schemalägg på söndag 19:00."

ChatGPT resolves the concrete Stockholm date/time from the conversation and calls `schedule_postiz`. The same ContentRun keeps its Postiz external IDs so performance can later feed the existing ML pipeline.
