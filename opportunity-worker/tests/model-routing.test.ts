import { describe, expect, it } from "vitest";
import { resolveModelAttempts } from "../src/model-routing.js";

const env = {
  OPENROUTER_API_KEY: "test-openrouter-key",
};

describe("resolveModelAttempts", () => {
  it("uses GLM 5.2 free first and OpenRouter Free as the only automatic fallback", () => {
    const attempts = resolveModelAttempts("free", env);

    expect(attempts.map(({ provider, model }) => ({ provider, model }))).toEqual([
      { provider: "openrouter", model: "z-ai/glm-5.2:free" },
      { provider: "openrouter", model: "openrouter/free" },
    ]);
  });

  it("uses GLM 5.3 Flash only when premium is explicitly requested", () => {
    const attempts = resolveModelAttempts("premium", env);

    expect(attempts.map(({ model }) => model)).toEqual(["z-ai/glm-5.3-flash"]);
  });

  it("uses Qwen3.8 Max 0902 only when premium max is explicitly requested", () => {
    const attempts = resolveModelAttempts("premium_max", env);

    expect(attempts.map(({ model }) => model)).toEqual(["qwen/qwen3.8-max-0902"]);
  });

  it("does not silently downgrade a paid tier to free models", () => {
    expect(resolveModelAttempts("premium", env)).toHaveLength(1);
    expect(resolveModelAttempts("premium_max", env)).toHaveLength(1);
  });

  it("supports Railway model overrides without changing tier semantics", () => {
    const attempts = resolveModelAttempts("free", {
      ...env,
      OPENROUTER_MODEL: "custom/free-primary",
      OPENROUTER_FREE_FALLBACK_MODEL: "custom/free-fallback",
    });

    expect(attempts.map(({ model }) => model)).toEqual([
      "custom/free-primary",
      "custom/free-fallback",
    ]);
  });
});
