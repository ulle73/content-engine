import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

describe("branch-only BUILD policy", () => {
  it("never advances the original GitHub target branch from the worker server", () => {
    const server = readFileSync(resolve(process.cwd(), "src/server.ts"), "utf8");

    expect(server).not.toContain("finalizeGitHubBuild");
    expect(server).not.toContain("GITHUB_AUTODEPLOY_TARGETS");
  });
});
