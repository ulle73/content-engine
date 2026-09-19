import { once } from "node:events";
import type { AddressInfo } from "node:net";
import type { Server } from "node:http";
import { afterEach, describe, expect, it } from "vitest";
import { signHmac } from "../src/auth.js";
import type { GitHubRefClient } from "../src/github-deploy.js";
import { createWorkerServer, type WorkerConfig } from "../src/server.js";
import type { JobProgress } from "../src/types.js";

const baseSha = "1".repeat(40);
const headSha = "2".repeat(40);

const config: WorkerConfig = {
  workerHmacSecret: "worker-secret",
  callbackHmacSecret: "callback-secret",
  allowPrivateUnsigned: false,
  publicDomain: "worker.example.com",
  githubToken: "github-token",
  openAiApiKey: "openai-key",
  githubAutomergeRepos: "ulle73/content-engine",
  githubAutodeployTargets: "ulle73/content-engine@opportunity-os-qa",
  n8nApiKey: "",
  railwayApiToken: "",
  shopifyAdminAccessToken: "",
  shopifyExperimentThemeId: "",
};

const finalizeJob = {
  jobId: "JOB-finalize-1",
  targetType: "github" as const,
  targetRef: "ulle73/content-engine@opportunity-os-qa",
  callbackUrl: "https://callback.invalid/finalize",
  callbackNonce: "nonce-1",
  rollback: {
    repo: "ulle73/content-engine",
    branch: "opportunity-os-qa",
    baseSha,
    headSha,
    workBranch: "opportunity-os/opp-1",
  },
};

class FinalizeClient implements GitHubRefClient {
  refs = new Map([
    ["ulle73/content-engine@opportunity-os-qa", baseSha],
    ["ulle73/content-engine@opportunity-os/opp-1", headSha],
  ]);
  updates: string[] = [];
  pullRequestGate?: Promise<void>;

  async getRef(repo: string, branch: string) {
    const value = this.refs.get(`${repo}@${branch}`);
    if (!value) throw new Error("missing ref");
    return value;
  }

  async setRef(repo: string, branch: string, sha: string) {
    this.updates.push(`${repo}@${branch}:${sha}`);
    this.refs.set(`${repo}@${branch}`, sha);
  }

  async restoreRef(repo: string, branch: string, sha: string) {
    this.refs.set(`${repo}@${branch}`, sha);
  }

  async createOrReusePullRequest() {
    await this.pullRequestGate;
    return { url: "https://github.com/ulle73/content-engine/pull/42" };
  }
}

class VerificationFailureClient extends FinalizeClient {
  private targetReads = 0;

  override async getRef(repo: string, branch: string) {
    if (branch === "opportunity-os-qa" && ++this.targetReads === 4) return "verification-mismatch";
    return super.getRef(repo, branch);
  }
}

class DeploymentFailureClient extends FinalizeClient {
  override async setRef() {
    throw new Error("GitHub ref update failed");
  }
}

const servers: Server[] = [];
afterEach(async () => {
  await Promise.all(servers.splice(0).map(async (server) => {
    if (server.listening) {
      server.close();
      await once(server, "close");
    }
  }));
});

async function start(server: Server): Promise<string> {
  servers.push(server);
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  const address = server.address() as AddressInfo;
  return `http://127.0.0.1:${address.port}`;
}

function signedHeaders(raw: string) {
  const timestamp = String(Math.floor(Date.now() / 1000));
  return {
    "content-type": "application/json",
    "x-os-timestamp": timestamp,
    "x-os-signature": signHmac(config.workerHmacSecret, timestamp, raw),
  };
}

describe("POST /v1/finalize", () => {
  it("uses the jobs authentication policy and rejects invalid rollback metadata", async () => {
    const client = new FinalizeClient();
    const server = createWorkerServer(config, { githubClient: client });
    const url = await start(server);
    const raw = JSON.stringify({
      ...finalizeJob,
      rollback: { ...finalizeJob.rollback, branch: "main" },
    });

    const unauthorized = await fetch(`${url}/v1/finalize`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: raw,
    });
    expect(unauthorized.status).toBe(401);

    const invalid = await fetch(`${url}/v1/finalize`, {
      method: "POST",
      headers: signedHeaders(raw),
      body: raw,
    });
    expect(invalid.status).toBe(400);
    expect(await invalid.json()).toEqual({ error: "invalid_job" });
    expect(client.updates).toEqual([]);
  });

  it("accepts only GitHub finalization jobs", async () => {
    const server = createWorkerServer(config, { githubClient: new FinalizeClient() });
    const url = await start(server);
    const raw = JSON.stringify({ ...finalizeJob, targetType: "railway" });

    const response = await fetch(`${url}/v1/finalize`, {
      method: "POST",
      headers: signedHeaders(raw),
      body: raw,
    });

    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({ error: "invalid_job" });
  });

  it("prevents duplicate concurrent finalization and reports the PR on every transition", async () => {
    let releasePullRequest!: () => void;
    const client = new FinalizeClient();
    client.pullRequestGate = new Promise<void>((resolve) => { releasePullRequest = resolve; });
    const progress: JobProgress[] = [];
    let finish!: () => void;
    const finished = new Promise<void>((resolve) => { finish = resolve; });
    const server = createWorkerServer(config, {
      githubClient: client,
      sendCallback: async (_job, update) => {
        progress.push(update);
        if (update.status === "SUCCEEDED") finish();
      },
    });
    const url = await start(server);
    const raw = JSON.stringify(finalizeJob);

    const first = await fetch(`${url}/v1/finalize`, {
      method: "POST",
      headers: signedHeaders(raw),
      body: raw,
    });
    const duplicate = await fetch(`${url}/v1/finalize`, {
      method: "POST",
      headers: signedHeaders(raw),
      body: raw,
    });

    expect(first.status).toBe(202);
    expect(await first.json()).toMatchObject({ accepted: true, status: "DEPLOYING" });
    expect(duplicate.status).toBe(409);
    expect(await duplicate.json()).toEqual({ error: "job_active" });

    releasePullRequest();
    await finished;
    expect(progress.map(({ status }) => status)).toEqual(["DEPLOYING", "VERIFYING", "SUCCEEDED"]);
    expect(progress.every(({ resultRef }) => resultRef === "https://github.com/ulle73/content-engine/pull/42")).toBe(true);
    expect(client.updates).toHaveLength(1);
  });

  it("allows unsigned finalization only in private unsigned mode without a public domain", async () => {
    let finish!: () => void;
    const finished = new Promise<void>((resolve) => { finish = resolve; });
    const server = createWorkerServer({ ...config, allowPrivateUnsigned: true, publicDomain: "" }, {
      githubClient: new FinalizeClient(),
      sendCallback: async (_job, update) => {
        if (update.status === "SUCCEEDED") finish();
      },
    });
    const url = await start(server);

    const response = await fetch(`${url}/v1/finalize`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(finalizeJob),
    });

    expect(response.status).toBe(202);
    await finished;
  });

  it("reports a verified rollback with the audit PR URL", async () => {
    const progress: JobProgress[] = [];
    let finish!: () => void;
    const finished = new Promise<void>((resolve) => { finish = resolve; });
    const client = new VerificationFailureClient();
    const server = createWorkerServer(config, {
      githubClient: client,
      sendCallback: async (_job, update) => {
        progress.push(update);
        if (update.status === "ROLLED_BACK") finish();
      },
    });
    const url = await start(server);
    const raw = JSON.stringify(finalizeJob);

    const response = await fetch(`${url}/v1/finalize`, {
      method: "POST",
      headers: signedHeaders(raw),
      body: raw,
    });

    expect(response.status).toBe(202);
    await finished;
    expect(progress.map(({ status }) => status)).toEqual(["DEPLOYING", "VERIFYING", "ROLLED_BACK"]);
    expect(progress.at(-1)?.resultRef).toBe("https://github.com/ulle73/content-engine/pull/42");
    expect(client.refs.get("ulle73/content-engine@opportunity-os-qa")).toBe(baseSha);
  });

  it("sends finalization failure reasons to n8n and preserves the audit PR URL", async () => {
    const progress: JobProgress[] = [];
    let finish!: () => void;
    const finished = new Promise<void>((resolve) => { finish = resolve; });
    const server = createWorkerServer(config, {
      githubClient: new DeploymentFailureClient(),
      sendCallback: async (_job, update) => {
        progress.push(update);
        if (update.status === "FAILED") finish();
      },
    });
    const url = await start(server);
    const raw = JSON.stringify(finalizeJob);

    const response = await fetch(`${url}/v1/finalize`, {
      method: "POST",
      headers: signedHeaders(raw),
      body: raw,
    });

    expect(response.status).toBe(202);
    await finished;
    expect(progress.at(-1)).toMatchObject({
      status: "FAILED",
      phase: "finalization_failed",
      resultRef: "https://github.com/ulle73/content-engine/pull/42",
      error: "GitHub ref update failed",
    });
  });
});

describe("GET /v1/capabilities", () => {
  it("reports whether the exact auto-deploy target allowlist is configured", async () => {
    const enabledServer = createWorkerServer(config, { githubClient: new FinalizeClient() });
    const enabledUrl = await start(enabledServer);
    const enabled = await fetch(`${enabledUrl}/v1/capabilities`);
    expect((await enabled.json()).github.autoDeployTargetsConfigured).toBe(true);

    const disabledServer = createWorkerServer({ ...config, githubAutodeployTargets: "" }, { githubClient: new FinalizeClient() });
    const disabledUrl = await start(disabledServer);
    const disabled = await fetch(`${disabledUrl}/v1/capabilities`);
    expect((await disabled.json()).github.autoDeployTargetsConfigured).toBe(false);
  });
});
