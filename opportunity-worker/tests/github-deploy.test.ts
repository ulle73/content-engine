import { describe, expect, it } from "vitest";
import {
  createGitHubRefClient,
  deployVerifiedRevision,
  finalizeGitHubBuild,
  isAutoDeployTarget,
  rollbackVerifiedRevision,
  type GitHubRefClient,
} from "../src/github-deploy.js";

class MemoryRefClient implements GitHubRefClient {
  refs = new Map<string, string>();
  updates: Array<{ repo: string; branch: string; sha: string }> = [];
  restores: Array<{ repo: string; branch: string; sha: string }> = [];
  pullRequests: Array<{ repo: string; baseBranch: string; headBranch: string }> = [];

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

  async createOrReusePullRequest(repo: string, baseBranch: string, headBranch: string) {
    this.pullRequests.push({ repo, baseBranch, headBranch });
    return { url: `https://github.com/${repo}/pull/42` };
  }
}

describe("isAutoDeployTarget", () => {
  it("requires an exact repository and branch pair", () => {
    const allow = "ulle73/content-engine@opportunity-os-qa";
    expect(isAutoDeployTarget("ulle73/content-engine", "opportunity-os-qa", allow)).toBe(true);
    expect(isAutoDeployTarget("ulle73/content-engine", "main", allow)).toBe(false);
    expect(isAutoDeployTarget("other/content-engine", "opportunity-os-qa", allow)).toBe(false);
  });
});

describe("deployVerifiedRevision", () => {
  it("moves the target only when it still equals the captured base SHA", async () => {
    const client = new MemoryRefClient();
    client.refs.set("ulle73/content-engine@opportunity-os-qa", "base123");
    client.refs.set("ulle73/content-engine@opportunity-os/opp-1", "head456");

    const result = await deployVerifiedRevision({
      client,
      repo: "ulle73/content-engine",
      branch: "opportunity-os-qa",
      baseSha: "base123",
      headSha: "head456",
      workBranch: "opportunity-os/opp-1",
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
      workBranch: "opportunity-os/opp-1",
    })).rejects.toThrow("Target branch moved");

    expect(client.updates).toEqual([]);
  });

  it("rejects a worker branch that no longer equals the captured head SHA", async () => {
    const client = new MemoryRefClient();
    client.refs.set("ulle73/content-engine@opportunity-os-qa", "base123");
    client.refs.set("ulle73/content-engine@opportunity-os/opp-1", "different-head");

    await expect(deployVerifiedRevision({
      client,
      repo: "ulle73/content-engine",
      branch: "opportunity-os-qa",
      baseSha: "base123",
      headSha: "head456",
      workBranch: "opportunity-os/opp-1",
    })).rejects.toThrow("Work branch moved");

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

  it("reuses an existing open audit pull request", async () => {
    const calls: Array<{ url: string; method: string }> = [];
    const request = async (url: string, init?: RequestInit) => {
      calls.push({ url, method: String(init?.method || "GET") });
      return new Response(JSON.stringify([{
        html_url: "https://github.com/ulle73/content-engine/pull/12",
        base: { ref: "opportunity-os-qa", repo: { full_name: "ulle73/content-engine" } },
        head: { ref: "opportunity-os/opp-1", repo: { full_name: "ulle73/content-engine" } },
      }]), { status: 200 });
    };

    const client = createGitHubRefClient("token-value", request as typeof fetch);
    await expect(client.createOrReusePullRequest(
      "ulle73/content-engine",
      "opportunity-os-qa",
      "opportunity-os/opp-1",
    )).resolves.toEqual({ url: "https://github.com/ulle73/content-engine/pull/12" });

    expect(calls).toHaveLength(1);
    expect(calls[0].method).toBe("GET");
    expect(calls[0].url).toContain("/repos/ulle73/content-engine/pulls?");
    expect(calls[0].url).toContain("base=opportunity-os-qa");
  });

  it("creates an audit pull request when no matching open request exists", async () => {
    const calls: Array<{ method: string; body: string }> = [];
    const request = async (_url: string, init?: RequestInit) => {
      const method = String(init?.method || "GET");
      calls.push({ method, body: String(init?.body || "") });
      if (method === "GET") return new Response("[]", { status: 200 });
      return new Response(JSON.stringify({ html_url: "https://github.com/ulle73/content-engine/pull/42" }), { status: 201 });
    };

    const client = createGitHubRefClient("token-value", request as typeof fetch);
    await expect(client.createOrReusePullRequest(
      "ulle73/content-engine",
      "opportunity-os-qa",
      "opportunity-os/opp-1",
    )).resolves.toEqual({ url: "https://github.com/ulle73/content-engine/pull/42" });

    expect(calls.map((call) => call.method)).toEqual(["GET", "POST"]);
    expect(JSON.parse(calls[1].body)).toMatchObject({
      base: "opportunity-os-qa",
      head: "opportunity-os/opp-1",
    });
  });
});


describe("finalizeGitHubBuild", () => {
  it("fails closed before deployment when the exact target is not approved", async () => {
    const client = new MemoryRefClient();
    client.refs.set("ulle73/content-engine@main", "base123");
    const statuses: Array<{ status: string; resultRef?: string; error?: string }> = [];

    const status = await finalizeGitHubBuild({
      client,
      repo: "ulle73/content-engine",
      branch: "main",
      baseSha: "base123",
      headSha: "head456",
      workBranch: "opportunity-os/opp-1",
      allowTargets: "ulle73/content-engine@opportunity-os-qa",
      onStatus: async (status, resultRef, error?: string) => { statuses.push({ status, resultRef, error }); },
    });

    expect(status).toBe("FAILED");
    expect(statuses).toEqual([{
      status: "FAILED",
      resultRef: undefined,
      error: "Auto-deploy target is not allowlisted: ulle73/content-engine@main",
    }]);
    expect(client.updates).toEqual([]);
    expect(client.pullRequests).toEqual([]);
  });

  it("deploys, verifies and succeeds for an exact approved target", async () => {
    const client = new MemoryRefClient();
    client.refs.set("ulle73/content-engine@opportunity-os-qa", "base123");
    client.refs.set("ulle73/content-engine@opportunity-os/opp-1", "head456");
    const statuses: Array<{ status: string; resultRef?: string }> = [];

    const status = await finalizeGitHubBuild({
      client,
      repo: "ulle73/content-engine",
      branch: "opportunity-os-qa",
      baseSha: "base123",
      headSha: "head456",
      workBranch: "opportunity-os/opp-1",
      allowTargets: "ulle73/content-engine@opportunity-os-qa",
      onStatus: async (status, resultRef) => { statuses.push({ status, resultRef }); },
    });

    expect(status).toBe("SUCCEEDED");
    expect(statuses).toEqual([
      { status: "DEPLOYING", resultRef: "https://github.com/ulle73/content-engine/pull/42" },
      { status: "VERIFYING", resultRef: "https://github.com/ulle73/content-engine/pull/42" },
      { status: "SUCCEEDED", resultRef: "https://github.com/ulle73/content-engine/pull/42" },
    ]);
    expect(client.pullRequests).toEqual([{
      repo: "ulle73/content-engine",
      baseBranch: "opportunity-os-qa",
      headBranch: "opportunity-os/opp-1",
    }]);
    expect(await client.getRef("ulle73/content-engine", "opportunity-os-qa")).toBe("head456");
  });

  it("fails before creating a PR when the worker branch head changed", async () => {
    const client = new MemoryRefClient();
    client.refs.set("ulle73/content-engine@opportunity-os-qa", "base123");
    client.refs.set("ulle73/content-engine@opportunity-os/opp-1", "different-head");
    const statuses: Array<{ status: string; error?: string }> = [];

    const status = await finalizeGitHubBuild({
      client,
      repo: "ulle73/content-engine",
      branch: "opportunity-os-qa",
      baseSha: "base123",
      headSha: "head456",
      workBranch: "opportunity-os/opp-1",
      allowTargets: "ulle73/content-engine@opportunity-os-qa",
      onStatus: async (status, _resultRef, error?: string) => { statuses.push({ status, error }); },
    });

    expect(status).toBe("FAILED");
    expect(statuses).toEqual([{ status: "FAILED", error: "Work branch moved after build completed" }]);
    expect(client.pullRequests).toEqual([]);
    expect(client.updates).toEqual([]);
  });

  it("reports when the target ref drifted before finalization", async () => {
    const client = new MemoryRefClient();
    client.refs.set("ulle73/content-engine@opportunity-os-qa", "different-base");
    const statuses: Array<{ status: string; error?: string }> = [];

    const status = await finalizeGitHubBuild({
      client,
      repo: "ulle73/content-engine",
      branch: "opportunity-os-qa",
      baseSha: "base123",
      headSha: "head456",
      workBranch: "opportunity-os/opp-1",
      allowTargets: "ulle73/content-engine@opportunity-os-qa",
      onStatus: async (value, _resultRef, error?: string) => { statuses.push({ status: value, error }); },
    });

    expect(status).toBe("FAILED");
    expect(statuses).toEqual([{ status: "FAILED", error: "Target branch moved after build started" }]);
    expect(client.pullRequests).toEqual([]);
    expect(client.updates).toEqual([]);
  });

  it("reports GitHub pull request API errors without exposing response details", async () => {
    const request = async (url: string, init?: RequestInit) => {
      if (url.includes("/git/ref/heads/opportunity-os-qa")) {
        return new Response(JSON.stringify({ object: { sha: "base123" } }), { status: 200 });
      }
      if (url.includes("/git/ref/heads/opportunity-os%2Fopp-1")) {
        return new Response(JSON.stringify({ object: { sha: "head456" } }), { status: 200 });
      }
      if (String(init?.method || "GET") === "GET") return new Response("[]", { status: 200 });
      return new Response("sensitive-provider-detail", { status: 503 });
    };
    const client = createGitHubRefClient("token-value", request as typeof fetch);
    const statuses: Array<{ status: string; error?: string }> = [];

    const status = await finalizeGitHubBuild({
      client,
      repo: "ulle73/content-engine",
      branch: "opportunity-os-qa",
      baseSha: "base123",
      headSha: "head456",
      workBranch: "opportunity-os/opp-1",
      allowTargets: "ulle73/content-engine@opportunity-os-qa",
      onStatus: async (value, _resultRef, error?: string) => { statuses.push({ status: value, error }); },
    });

    expect(status).toBe("FAILED");
    expect(statuses).toEqual([{ status: "FAILED", error: "GitHub API failed (503)" }]);
    expect(statuses[0].error).not.toContain("sensitive-provider-detail");
  });

  it("rolls back when post-deploy verification fails", async () => {
    const client = new MemoryRefClient();
    client.refs.set("ulle73/content-engine@opportunity-os-qa", "base123");
    client.refs.set("ulle73/content-engine@opportunity-os/opp-1", "head456");
    const statuses: string[] = [];

    const status = await finalizeGitHubBuild({
      client,
      repo: "ulle73/content-engine",
      branch: "opportunity-os-qa",
      baseSha: "base123",
      headSha: "head456",
      workBranch: "opportunity-os/opp-1",
      allowTargets: "ulle73/content-engine@opportunity-os-qa",
      verify: async () => false,
      onStatus: async (value) => { statuses.push(value); },
    });

    expect(status).toBe("ROLLED_BACK");
    expect(statuses).toEqual(["DEPLOYING", "VERIFYING", "ROLLED_BACK"]);
    expect(await client.getRef("ulle73/content-engine", "opportunity-os-qa")).toBe("base123");
  });

  it("does not roll back when the target moves again after deployment", async () => {
    const client = new MemoryRefClient();
    client.refs.set("ulle73/content-engine@opportunity-os-qa", "base123");
    client.refs.set("ulle73/content-engine@opportunity-os/opp-1", "head456");
    const statuses: Array<{ status: string; resultRef?: string; error?: string }> = [];

    const status = await finalizeGitHubBuild({
      client,
      repo: "ulle73/content-engine",
      branch: "opportunity-os-qa",
      baseSha: "base123",
      headSha: "head456",
      workBranch: "opportunity-os/opp-1",
      allowTargets: "ulle73/content-engine@opportunity-os-qa",
      verify: async () => {
        client.refs.set("ulle73/content-engine@opportunity-os-qa", "third-party-head");
        return false;
      },
      onStatus: async (status, resultRef, error?: string) => { statuses.push({ status, resultRef, error }); },
    });

    expect(status).toBe("FAILED");
    expect(statuses.at(-1)).toEqual({
      status: "FAILED",
      resultRef: "https://github.com/ulle73/content-engine/pull/42",
      error: "Post-deploy verification failed; rollback not attempted because target no longer matches deployed revision",
    });
    expect(client.restores).toEqual([]);
  });

  it("reports rollback failures and preserves the audit PR URL", async () => {
    const client = new MemoryRefClient();
    client.refs.set("ulle73/content-engine@opportunity-os-qa", "base123");
    client.refs.set("ulle73/content-engine@opportunity-os/opp-1", "head456");
    client.restoreRef = async () => { throw new Error("restore unavailable"); };
    const statuses: Array<{ status: string; resultRef?: string; error?: string }> = [];

    const status = await finalizeGitHubBuild({
      client,
      repo: "ulle73/content-engine",
      branch: "opportunity-os-qa",
      baseSha: "base123",
      headSha: "head456",
      workBranch: "opportunity-os/opp-1",
      allowTargets: "ulle73/content-engine@opportunity-os-qa",
      verify: async () => false,
      onStatus: async (value, resultRef, error?: string) => { statuses.push({ status: value, resultRef, error }); },
    });

    expect(status).toBe("FAILED");
    expect(statuses.at(-1)).toEqual({
      status: "FAILED",
      resultRef: "https://github.com/ulle73/content-engine/pull/42",
      error: "Post-deploy verification failed; rollback failed: restore unavailable",
    });
  });
});
