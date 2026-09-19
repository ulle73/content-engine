import { describe, expect, it } from "vitest";
import {
  deployVerifiedRevision,
  isAutoDeployTarget,
  type GitHubRefClient,
} from "../src/github-deploy.js";

class MemoryRefClient implements GitHubRefClient {
  refs = new Map<string, string>();
  updates: Array<{ repo: string; branch: string; sha: string }> = [];

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
