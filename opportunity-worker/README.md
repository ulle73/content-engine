# Golfkuponger Opportunity OS Worker

Long-running build worker for Opportunity OS. n8n owns policy and orchestration; this service only executes explicitly authorized, capability-gated build jobs.

## LLM routing

Build jobs prefer OpenRouter when `OPENROUTER_API_KEY` is configured. The default primary model is `nvidia/nemotron-3-ultra-550b-a55b:free`. If the OpenRouter attempt fails, the worker resets the worktree and retries with OpenAI using `OPENAI_API_KEY`; the default fallback model is `gpt-5.6-sol`.

Optional overrides:

- `OPENROUTER_MODEL`
- `OPENAI_FALLBACK_MODEL`

Provider credentials are available to the Codex process for API authentication but are excluded from the shell environment exposed to the coding agent. The worker also scans staged changes for configured secrets before committing.
