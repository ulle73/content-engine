import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

describe("Codex Railway compatibility version", () => {
  it("pins the Codex CLI and SDK to the Landlock-compatible 0.147.0 release", () => {
    const pkg = JSON.parse(readFileSync(resolve(process.cwd(), "package.json"), "utf8"));

    expect(pkg.dependencies["@openai/codex"]).toBe("0.147.0");
    expect(pkg.dependencies["@openai/codex-sdk"]).toBe("0.147.0");
  });
});
