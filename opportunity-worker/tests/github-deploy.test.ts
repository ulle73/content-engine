import { describe, expect, it } from "vitest";
import {
  createGitHubRefClient,
  deployVerifiedRevision,
  isAutoDeployTarget,
  rollbackVerifiedRevision,
  type GitHubRefClient,
} from "../src/github-deploy.js";

class MemoryRefClient implements GitHubRefClient {
  refs = new Map<string, string>();
  updates: Array<{ repo: string; branch: string; sha: string }> = [];
  restores: Array<{ repo: string; branch: string; sha: string }> = [];

  private key(repo: string, branch: string) {
    return repo + "@" + branch;
  }

  async getRef(repo: string, branch: string) {
    const value = this.refs.get(this.key(repo, branch));
    if (!value) throw new Error("missing ref");
    return value;
  }

  async setRef(repo: string, branch: string, sha: string) {
    this.updates.push({ repo, branch, sha });
    this.refs.set(this.key(repo, branch), sha);
  }

  async restoreRef(repo: string, branch: string, sha: string) {
    this.restores.push({ repo, branch, sha });
    this.refs.set(this.key(repo, branch), sha);
  }
}

describe("isAutoDeployTarget", () => {
  it("requires an exact repository and branch pair", () => {
    const allow = "ulle73/content-engine@opportunity-os-qa";
    expect(isAutoDeployTarget("ulle73/content-engine", "opportunity-os-qa", allow)).toBe(true);
    expect(isAutoDeployTarget("ulle73/content-engine", "main", allow)).toBe(false);
  });
});

describe("deployVerifiedRevision", () => {
  it("moves the target only when it still equals the captured base SHA", async () => {
    const client = new MemoryRefClient();
    client.refs.set("ulle73/content-engine@opportunity-os-qa", "base123");

    const result = await deployVerifiedRevision({
      client,
      repo: "ulle73/content-engine",
      branch: "opportunity-os-qa",
      baseSha: "base123",
      headSha: "head456",
    });

    expect(result.deployedSha).toBe("head456");
    expect(client.updates).toEqual([{ repo: "ulle73/content-engine", branch: "opportunity-os-qa", sha: "head456" }]);
  });

  it("rejects a target that moved after the build started", async () => {
    const client = new MemoryRefClient();
    client.refs.set("ulle73/content-engine@opportunity-os-qa", "someone-else");

    await expect(deployVerifiedRevision({
      client,
      repo: "ulle73/content-engine",
      branch: "opportunity-os-qa",
      baseSha: "base123",
      headSha: "head456",
    })).rejects.toThrow("Target branch moved");

    expect(client.updates).toEqual([]);
  });
});


describe("rollbackVerifiedRevision", () => {
  it("restores the captured base only while the deployed SHA is still current", async () => {
    const client = new MemoryRefClient();
    client.refs.set("ulle73/content-engine@opportunity-os-qa", "head456");

    const result = await rollbackVerifiedRevision({
      client,
      repo: "ulle73/content-engine",
      branch: "opportunity-os-qa",
      baseSha: "base123",
      deployedSha: "head456",
    });

    expect(result).toEqual({ ok: true, restoredSha: "base123" });
    expect(client.restores).toEqual([{ repo: "ulle73/content-engine", branch: "opportunity-os-qa", sha: "base123" }]);
  });

  it("refuses rollback after a third party moves the target", async () => {
    const client = new MemoryRefClient();
    client.refs.set("ulle73/content-engine@opportunity-os-qa", "newer789");

    await expect(rollbackVerifiedRevision({
      client,
      repo: "ulle73/content-engine",
      branch: "opportunity-os-qa",
      baseSha: "base123",
      deployedSha: "head456",
    })).rejects.toThrow("Refusing rollback");

    expect(client.restores).toEqual([]);
  });
});


describe("createGitHubRefClient", () => {
  it("reads and advances a branch through the GitHub refs API", async () => {
    const calls: Array<{ url: string; method: string; body: string }> = [];
    const request = async (url: string, init?: RequestInit) => {
      const method = String(init?.method || "GET");
      const body = String(init?.body || "");
      calls.push({ url, method, body });
      if (method === "GET") {
        return new Response(JSON.stringify({ object: { sha: "base123" } }), { status: 200 });
      }
      return new Response(JSON.stringify({ object: { sha: "head456" } }), { status: 200 });
    };

    const client = createGitHubRefClient("token-value", request as typeof fetch);
    expect(await client.getRef("ulle73/content-engine", "opportunity-os-qa")).toBe("base123");
    await client.setRef("ulle73/content-engine", "opportunity-os-qa", "head456");

    expect(calls[0].method).toBe("GET");
    expect(calls[0].url).toContain("/repos/ulle73/content-engine/git/ref/heads/opportunity-os-qa");
    expect(calls[1].method).toBe("PATCH");
    expect(JSON.parse(calls[1].body)).toEqual({ sha: "head456", force: false });
  });

  it("uses an explicit rollback ref update", async () => {
    const calls: Array<{ method: string; body: string }> = [];
    const request = async (_url: string, init?: RequestInit) => {
      calls.push({ method: String(init?.method || "GET"), body: String(init?.body || "") });
      return new Response(JSON.stringify({ object: { sha: "base123" } }), { status: 200 });
    };

    const client = createGitHubRefClient("token-value", request as typeof fetch);
    await client.restoreRef("ulle73/content-engine", "opportunity-os-qa", "base123");

    expect(calls[0].method).toBe("PATCH");
    expect(JSON.parse(calls[0].body)).toEqual({ sha: "base123", force: true });
  });
});
