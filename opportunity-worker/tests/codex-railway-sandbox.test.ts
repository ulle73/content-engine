import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

describe("Codex Railway execution boundary", () => {
  it("uses an unprivileged full-access Codex process with secret-safe git and shell env", () => {
    const source = readFileSync(resolve(process.cwd(), "src/codex-runner.ts"), "utf8");

    expect(existsSync("/usr/local/bin/codex-unprivileged")).toBe(true);
    expect(source).toContain('codexPathOverride: "/usr/local/bin/codex-unprivileged"');
    expect(source).toContain('sandboxMode: "danger-full-access"');
    expect(source).not.toContain("use_legacy_landlock");
    expect(source).not.toContain("https://x-access-token:");
    expect(source).toContain("http.extraHeader=Authorization: Basic");
    expect(source).toContain("shell_environment_policy");
    expect(source).toContain('inherit: "core"');
    expect(source).toContain("ignore_default_excludes: false");
    expect(source).toContain("include_only");
  });
});
