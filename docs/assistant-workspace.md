# Conversational studio

The Skapa navigation opens `/company/<uuid>/studio/`. The previous form workflow
remains available through Formulärläge. Everything uses the existing company,
MediaAsset, MediaGeneration, Sequence and Motion services and storage.

## Approval lifecycle

1. A bounded OpenRouter vision/text call interprets the request, company facts,
   selected template and ordered attachments. It asks up to three clarifying
   questions. It cannot execute tools, assign asset IDs or approve spending.
2. A deterministic review validates model capabilities and displays the selected
   and recommended model, dimensions, crop/upscale risks, clip count, planning
   prices and the user's maximum generation cost in USD. Unknown prices are
   explicitly unknown. Planning prices are dated hints, not binding quotes.
   No generation jobs or image normalization are created at this stage.
3. **Bekräfta upplägget och optimera** recompiles the confirmed request against
   the trusted model/recipe registries. It creates new contain/crop image copies
   according to the user's selected policy and preserves originals. It saves
   optimized prompts and queued media jobs, an immutable Motion project or an
   existing content draft. Provider price checks do not start generations.
4. Each paid start requires an explicit button, a current plan revision, unchanged
   source hashes, a fresh authenticated estimate, and a verified total cost no
   greater than the user's budget. The entire order is reserved, including all
   transitions, rather than just the selected clip. The existing server cost
   ceiling still applies to each clip. Missing prices stop paid start; OpenAI
   image generation currently cannot satisfy a hard maximum because its adapter
   does not provide a binding price estimate.
5. Generated assets appear in the conversation and the shared library. Original
   logos and uploaded music are composed with Motion after video generation.
   A current approved Motion preview is mandatory before final rendering.
   Rendering uses the existing connected local renderer; no paid always-on
   infrastructure is provisioned.

The maximum applies to media generation for this plan. Text/vision planning calls
are separately metered and their reported cost is shown. It is not a monthly
account spending limit. Queued jobs are never started by polling. Edited briefs,
budgets, attachment order or templates need a new turn and a new approval.

## Animated scroll

`animated-scroll` is a built-in sequence template. N ordered images create N−1
adjacent clips using the trusted `scroll_transition_bridge` recipe. Each clip
uses canonical locked start/end anchors, the explicitly selected compatible
model (or the recommended Auto choice), and an individual optimized prompt.
Start/end roles must match the first/last positions. An explicit duration in the
brief is respected; the default is 5 seconds per transition.

Quality recommendations rank only enabled models with verified contracts and
matching reference roles, durations and recipe capabilities. Known affordable
models are preferred; unknown prices require a provider check. No manually
selected model is silently replaced. The recommendation is based on registry
quality profiles, not a universal benchmark of every model on the market.

480p may fit the existing per-clip cost ceiling but cannot meet the current sharp
Motion film export threshold. Review warns before spending. For Seedance 2.5,
4-second 720p clips may be a useful alternative if the total budget permits.
AI transitions may morph details. A finished film still requires inspection and
Motion preview approval. Normalization does not invent missing image detail.

## Extension points

- **Templates:** add a `PromptTemplate` in `engine/assistant/templates.py`, or save
  a company-scoped version in the UI. Templates are instruction data. Only
  `{{brief}}`, `{{company_name}}`, `{{profile}}`, `{{voice}}`, `{{current}}` are
  substituted. Python/Jinja is never executed. Existing plans retain snapshots.
- **Workflows:** implement pure `compile` and non-billable `prepare` adapters,
  register `WorkflowDefinition`, and add the ID to the closed public/LLM contracts.
  Return validated schemas and reuse the engine's existing approval services.
  The chat catalogue is generated from the registry.
- **Models:** update the verified creative model registry and provider adapter
  with primary-source evidence. The assistant does not bypass capability checks.
- **Actions:** add a closed ActionRequest operation, an authorized service branch,
  and a UI action. Never turn model-generated strings into executable operations.

`AssistantConversation` and `AssistantTurn` own durable history and revisions.
`AssistantPlan.spec` is fingerprinted and retained unchanged; optimized artifacts
are in `prepared`. Provider planning runs outside transactions. Claim leases,
client idempotency keys, company row ownership and PostgreSQL locks fence
duplicates, stale responses, cross-company access and concurrent confirmations.
Browser rendering uses DOM textContent, CSRF-protected POSTs and company-scoped
URLs. Private images are resized to bounded vision inputs, not public URLs.

## Configuration and checks

- Existing `OPENROUTER_API_KEY`; optional `OPENROUTER_ASSISTANT_MODEL` defaults to
  `google/gemini-2.5-flash`. One call, 2400 output tokens, 40-second timeout,
  structured schema, no automatic paid fallback. Media model is a separate choice.
- Migration `0026_assistant_workspace` adds studio history and template tables.
  Existing locked migration deployment handles it.
- `manage.py test engine.test_assistant --settings=engine.test_settings`
- `scripts/assistant_postgres_tests.py` uses only 127.0.0.1:55439 and the named
  disposable `content_engine_assistant_test` database, never production `.env`.
- `scripts/assistant_ui_fixture.py` serves isolated synthetic browser fixtures
  on 127.0.0.1:8771 with mocked planning and price checks, local storage and a
  separate SQLite database. It does not load production credentials.

Production provider, R2 and final render behavior must be distinguished from
mocked acceptance tests. Never start paid media work as part of automated UI QA.
