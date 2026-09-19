import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

describe("Codex Railway sandbox compatibility", () => {
  it("keeps workspace-write and enables the legacy Landlock backend", () => {
    const source = readFileSync(resolve(process.cwd(), "src/codex-runner.ts"), "utf8");

    expect(source).toContain('sandboxMode: "workspace-write"');
    expect(source).toContain("use_legacy_landlock: true");
    expect(source).not.toContain('sandboxMode: "danger-full-access"');
  });
});
