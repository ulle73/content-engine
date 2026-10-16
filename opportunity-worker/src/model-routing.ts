import type { BuildModelTier } from "./types.js";

export type LlmAttempt = {
  provider: "openrouter";
  model: string;
  apiKey: string;
};

const DEFAULT_FREE_MODEL = "z-ai/glm-5.2:free";
const DEFAULT_FREE_FALLBACK_MODEL = "openrouter/free";
const DEFAULT_PREMIUM_MODEL = "z-ai/glm-5.3-flash";
const DEFAULT_PREMIUM_MAX_MODEL = "qwen/qwen3.8-max-0902";

type Env = Record<string, string | undefined>;

export function isBuildModelTier(value: unknown): value is BuildModelTier {
  return value === "free" || value === "premium" || value === "premium_max";
}

function model(env: Env, key: string, fallback: string): string {
  return (env[key] ?? "").trim() || fallback;
}

export function resolveModelAttempts(
  tier: BuildModelTier = "free",
  env: Env = process.env,
): LlmAttempt[] {
  const apiKey = (env.OPENROUTER_API_KEY ?? "").trim();
  if (!apiKey) return [];

  if (tier === "premium") {
    return [{
      provider: "openrouter",
      model: model(env, "OPENROUTER_PREMIUM_MODEL", DEFAULT_PREMIUM_MODEL),
      apiKey,
    }];
  }

  if (tier === "premium_max") {
    return [{
      provider: "openrouter",
      model: model(env, "OPENROUTER_PREMIUM_MAX_MODEL", DEFAULT_PREMIUM_MAX_MODEL),
      apiKey,
    }];
  }

  const primary = model(env, "OPENROUTER_MODEL", DEFAULT_FREE_MODEL);
  const fallback = model(env, "OPENROUTER_FREE_FALLBACK_MODEL", DEFAULT_FREE_FALLBACK_MODEL);
  const models = primary === fallback ? [primary] : [primary, fallback];

  return models.map(modelName => ({
    provider: "openrouter" as const,
    model: modelName,
    apiKey,
  }));
}
