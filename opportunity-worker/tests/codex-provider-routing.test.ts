import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

describe("Codex provider routing", () => {
  it("prefers OpenRouter Nemotron free and retains OpenAI as fallback", () => {
    const source = readFileSync(resolve(process.cwd(), "src/codex-runner.ts"), "utf8");

    expect(source).toContain("OPENROUTER_API_KEY");
    expect(source).toContain('nvidia/nemotron-3-ultra-550b-a55b:free');
    expect(source).toContain('model_provider: "openrouter"');
    expect(source).toContain('base_url: "https://openrouter.ai/api/v1"');
    expect(source).toContain('wire_api: "responses"');
    expect(source).toContain("OPENAI_FALLBACK_MODEL");
    expect(source).toContain('gpt-5.6-sol');

    const openRouterAttempt = source.indexOf('provider: "openrouter"');
    const openAiAttempt = source.indexOf('provider: "openai"');
    expect(openRouterAttempt).toBeGreaterThanOrEqual(0);
    expect(openAiAttempt).toBeGreaterThan(openRouterAttempt);
  });

  it("does not expose provider credentials to the agent shell", () => {
    const source = readFileSync(resolve(process.cwd(), "src/codex-runner.ts"), "utf8");

    expect(source).toContain('include_only: ["PATH", "HOME", "TMPDIR", "USER", "LOGNAME", "LANG"]');
    expect(source).not.toContain('include_only: ["PATH", "HOME", "TMPDIR", "USER", "LOGNAME", "LANG", "OPENROUTER_API_KEY"]');
  });
});
