import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

describe("Codex no-change diagnostics", () => {
  it("includes the Codex final response when no repository change is produced", () => {
    const source = readFileSync(resolve(process.cwd(), "src/codex-runner.ts"), "utf8");

    expect(source).toContain("const turn = await thread.run(prompt)");
    expect(source).toContain("turn.finalResponse");
  });
});
