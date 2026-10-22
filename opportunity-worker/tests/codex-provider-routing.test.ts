import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

describe("Codex provider routing integration", () => {
  it("delegates model selection to the explicit OpenRouter tier router", () => {
    const source = readFileSync(resolve(process.cwd(), "src/codex-runner.ts"), "utf8");

    expect(source).toContain("resolveModelAttempts(modelTier)");
    expect(source).toContain('model_provider: "openrouter"');
    expect(source).toContain('base_url: "https://openrouter.ai/api/v1"');
    expect(source).toContain('wire_api: "responses"');
    expect(source).not.toContain("OPENAI_FALLBACK_MODEL");
    expect(source).not.toContain('provider: "openai"');
  });

  it("does not expose provider credentials to the agent shell", () => {
    const source = readFileSync(resolve(process.cwd(), "src/codex-runner.ts"), "utf8");

    expect(source).toContain('include_only: ["PATH", "HOME", "TMPDIR", "USER", "LOGNAME", "LANG"]');
    expect(source).not.toContain('include_only: ["PATH", "HOME", "TMPDIR", "USER", "LOGNAME", "LANG", "OPENROUTER_API_KEY"]');
  });
});
