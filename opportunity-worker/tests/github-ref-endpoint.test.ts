import { describe, expect, it } from "vitest";
import { createGitHubRefClient } from "../src/github-deploy.js";

describe("GitHub ref endpoint routing", () => {
  it("uses singular ref for GET and plural refs for PATCH", async () => {
    const calls: Array<{ url: string; method: string }> = [];
    const request = async (url: string, init?: RequestInit) => {
      const method = String(init?.method || "GET");
      calls.push({ url, method });
      if (method === "GET") {
        return new Response(JSON.stringify({ object: { sha: "base123" } }), { status: 200 });
      }
      return new Response(JSON.stringify({ object: { sha: "head456" } }), { status: 200 });
    };

    const client = createGitHubRefClient("token-value", request as typeof fetch);
    await client.getRef("ulle73/content-engine", "opportunity-os-spec");
    await client.setRef("ulle73/content-engine", "opportunity-os-spec", "head456");

    expect(calls[0].url).toContain("/git/ref/heads/opportunity-os-spec");
    expect(calls[1].url).toContain("/git/refs/heads/opportunity-os-spec");
  });
});
