# Motion Engine implementation plan

Goal: novice UI and authenticated MCP create the same validated MotionSpec, preview and final Remotion render, retained in existing company-scoped MediaAssets.

Architecture: Django owns projects, immutable revisions, durable render jobs, permissions, assets and storage. An isolated worker renders an allowlisted JSON contract with Remotion; no LLM or arbitrary code runs per frame. HyperFrames motion principles inform template choreography and pacing. Existing OAuth, Company, ContentRun, MediaGeneration, MediaAsset and R2 remain authoritative.

Scope: the 30 September 2026 Motion Engine acceptance brief; original retained in the task evidence. Production branch is feature/chatgpt-content-engine-mcp; main has diverged. Work only on feature/motion-engine-production until verification.

## Implementation and checks
1. Versioned catalogue, templates and strict MotionSpec: schema tests for unknown keys, IDs, unbounded timing, component/asset injection, duplicate IDs, media references.
2. Project/revision/render persistence: owner isolation, optimistic updates, immutable job snapshots, idempotency payload conflicts, preview approval, lease fencing, bounded retries and cancellation tests.
3. Remotion renderer: deterministic scene and effect registry, safe content area, fitting text, media, SVG, Lottie, audio envelopes. Compile/typecheck; render all ratios and decode audio/video.
4. Browser UI: two entry paths, catalogue previews, form schemas, storyboard, advanced editing, status and retained asset. Test browser mobile/desktop and keyboard flows.
5. Same functions exposed through existing MCP: annotations, authenticated discovery and full draft/preview/final/asset transport test.
6. Production integration: async worker, health/capacity checks, signed/scoped asset delivery, build/migrations and whole existing test suite. No paid upgrade or license purchase without approval.
7. Review third-party provenance, docs and router skill. Separate final novice/advanced/agent/failure/maintainer audit. Fix and rerun failures.

## Review focus
- Cross-company IDs and media must never be usable.
- User data must never select a URL, import, CSS, JavaScript, file path or executable.
- A stale worker cannot finish a re-leased job; cancellation fences all writes.
- A changed spec invalidates its preview, and final render requires review of that same hash.
- Long Swedish text and large numbers must fit in all aspect ratios.
- Render failures must leave the previous successful revision and assets available.
- Honest production readiness: no preview-less item is marked production ready; no mock integration passes an end-to-end gate.
