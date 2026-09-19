import { describe, expect, it } from "vitest";
import { isAutoDeployTarget } from "../src/github-deploy.js";

describe("isAutoDeployTarget", () => {
  it("requires an exact repository and branch pair", () => {
    const allow = "ulle73/content-engine@opportunity-os-qa";
    expect(isAutoDeployTarget("ulle73/content-engine", "opportunity-os-qa", allow)).toBe(true);
    expect(isAutoDeployTarget("ulle73/content-engine", "main", allow)).toBe(false);
  });
});
