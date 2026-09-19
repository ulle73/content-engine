export interface GitHubRefClient {
  getRef(repo: string, branch: string): Promise<string>;
  setRef(repo: string, branch: string, sha: string): Promise<void>;
  restoreRef(repo: string, branch: string, sha: string): Promise<void>;
  createOrReusePullRequest(repo: string, baseBranch: string, headBranch: string): Promise<{ url: string }>;
}

type RequestFn = typeof fetch;

function repoParts(repo: string): { owner: string; name: string } {
  const [owner, name] = repo.split("/");
  if (!owner || !name || repo.split("/").length !== 2) throw new Error("Invalid GitHub repository");
  return { owner, name };
}

function repoUrl(repo: string): string {
  const { owner, name } = repoParts(repo);
  return `https://api.github.com/repos/${encodeURIComponent(owner)}/${encodeURIComponent(name)}`;
}

function refUrl(repo: string, branch: string): string {
  return `${repoUrl(repo)}/git/ref/heads/${encodeURIComponent(branch)}`;
}

class GitHubApiError extends Error {
  readonly status: number;

  constructor(status: number, detail: string) {
    super(`GitHub API failed (${status}): ${detail}`);
    this.status = status;
  }
}

class PostDeployVerificationError extends Error {}

export function createGitHubRefClient(token: string, request: RequestFn = fetch): GitHubRefClient {
  if (!token) throw new Error("Missing GITHUB_TOKEN");

  async function call(url: string, init?: RequestInit): Promise<any> {
    const response = await request(url, {
      ...init,
      headers: {
        accept: "application/vnd.github+json",
        authorization: `Bearer ${token}`,
        "x-github-api-version": "2022-11-28",
        "content-type": "application/json",
        ...(init?.headers || {}),
      },
    });
    if (!response.ok) {
      const detail = (await response.text().catch(() => "")).slice(0, 1000);
      throw new GitHubApiError(response.status, detail);
    }
    return response.json();
  }

  async function findPullRequest(repo: string, baseBranch: string, headBranch: string): Promise<string> {
    const { owner } = repoParts(repo);
    const query = new URLSearchParams({
      state: "open",
      base: baseBranch,
      head: `${owner}:${headBranch}`,
    });
    const data = await call(`${repoUrl(repo)}/pulls?${query}`, { method: "GET" });
    if (!Array.isArray(data)) return "";
    const pullRequest = data.find((candidate) =>
      candidate?.base?.repo?.full_name === repo
      && candidate?.base?.ref === baseBranch
      && candidate?.head?.repo?.full_name === repo
      && candidate?.head?.ref === headBranch,
    );
    return String(pullRequest?.html_url || "");
  }

  return {
    async getRef(repo, branch) {
      const data = await call(refUrl(repo, branch), { method: "GET" });
      const sha = String(data?.object?.sha || "");
      if (!sha) throw new Error("GitHub ref response did not contain a SHA");
      return sha;
    },
    async setRef(repo, branch, sha) {
      await call(refUrl(repo, branch), { method: "PATCH", body: JSON.stringify({ sha, force: false }) });
    },
    async restoreRef(repo, branch, sha) {
      await call(refUrl(repo, branch), { method: "PATCH", body: JSON.stringify({ sha, force: true }) });
    },
    async createOrReusePullRequest(repo, baseBranch, headBranch) {
      const existingUrl = await findPullRequest(repo, baseBranch, headBranch);
      if (existingUrl) return { url: existingUrl };

      try {
        const data = await call(`${repoUrl(repo)}/pulls`, {
          method: "POST",
          body: JSON.stringify({
            title: `Opportunity OS audit: ${headBranch} to ${baseBranch}`,
            body: "Audit pull request for a verified Opportunity OS worker finalization.",
            head: headBranch,
            base: baseBranch,
          }),
        });
        const url = String(data?.html_url || "");
        if (!url) throw new Error("GitHub pull request response did not contain a URL");
        return { url };
      } catch (error) {
        if (!(error instanceof GitHubApiError) || error.status !== 422) throw error;
        const racedUrl = await findPullRequest(repo, baseBranch, headBranch);
        if (!racedUrl) throw error;
        return { url: racedUrl };
      }
    },
  };
}

export function isAutoDeployTarget(repo: string, branch: string, raw: string): boolean {
  const target = repo + "@" + branch;
  return new Set(raw.split(",").map((value) => value.trim()).filter(Boolean)).has(target);
}

export async function deployVerifiedRevision(args: {
  client: GitHubRefClient;
  repo: string;
  branch: string;
  baseSha: string;
  headSha: string;
  workBranch: string;
}) {
  const { client, repo, branch, baseSha, headSha, workBranch } = args;
  const current = await client.getRef(repo, branch);
  if (current !== baseSha) {
    throw new Error("Target branch moved after build started");
  }
  const workHead = await client.getRef(repo, workBranch);
  if (workHead !== headSha) {
    throw new Error("Work branch moved after build completed");
  }
  await client.setRef(repo, branch, headSha);
  let verified: string;
  try {
    verified = await client.getRef(repo, branch);
  } catch {
    throw new PostDeployVerificationError("Deployed revision verification failed");
  }
  if (verified !== headSha) {
    throw new PostDeployVerificationError("Deployed revision verification failed");
  }
  return { repo, branch, previousSha: baseSha, deployedSha: headSha };
}

export async function rollbackVerifiedRevision(args: {
  client: GitHubRefClient;
  repo: string;
  branch: string;
  baseSha: string;
  deployedSha: string;
}) {
  const { client, repo, branch, baseSha, deployedSha } = args;
  const current = await client.getRef(repo, branch);
  if (current !== deployedSha) {
    throw new Error("Refusing rollback because target changed after deployment");
  }
  await client.restoreRef(repo, branch, baseSha);
  const verified = await client.getRef(repo, branch);
  if (verified !== baseSha) {
    throw new Error("Rollback verification failed");
  }
  return { ok: true, restoredSha: baseSha };
}


export async function finalizeGitHubBuild(args: {
  client: GitHubRefClient;
  repo: string;
  branch: string;
  baseSha: string;
  headSha: string;
  workBranch: string;
  allowTargets: string;
  onStatus: (status: "DEPLOYING" | "VERIFYING" | "SUCCEEDED" | "ROLLED_BACK" | "FAILED", resultRef?: string) => Promise<void>;
  verify?: () => Promise<boolean>;
}): Promise<"SUCCEEDED" | "ROLLED_BACK" | "FAILED"> {
  const { client, repo, branch, baseSha, headSha, workBranch, allowTargets, onStatus } = args;
  if (!isAutoDeployTarget(repo, branch, allowTargets)) {
    await onStatus("FAILED");
    return "FAILED";
  }

  let pullRequestUrl: string | undefined;
  let rollbackAllowed = false;
  try {
    const currentTarget = await client.getRef(repo, branch);
    if (currentTarget !== baseSha) throw new Error("Target branch moved after build started");
    const currentWorkHead = await client.getRef(repo, workBranch);
    if (currentWorkHead !== headSha) throw new Error("Work branch moved after build completed");

    pullRequestUrl = (await client.createOrReusePullRequest(repo, branch, workBranch)).url;
    await onStatus("DEPLOYING", pullRequestUrl);
    await deployVerifiedRevision({ client, repo, branch, baseSha, headSha, workBranch });
    await onStatus("VERIFYING", pullRequestUrl);

    rollbackAllowed = true;
    const verified = args.verify ? await args.verify() : (await client.getRef(repo, branch)) === headSha;

    if (!verified) {
      throw new Error("Post-deploy verification failed");
    }

    rollbackAllowed = false;
    await onStatus("SUCCEEDED", pullRequestUrl);
    return "SUCCEEDED";
  } catch (error) {
    if (rollbackAllowed || error instanceof PostDeployVerificationError) {
      const current = await client.getRef(repo, branch).catch(() => "");
      if (current !== headSha) {
        await onStatus("FAILED", pullRequestUrl);
        return "FAILED";
      }
      try {
        await rollbackVerifiedRevision({ client, repo, branch, baseSha, deployedSha: headSha });
        await onStatus("ROLLED_BACK", pullRequestUrl);
        return "ROLLED_BACK";
      } catch {
        await onStatus("FAILED", pullRequestUrl);
        return "FAILED";
      }
    }

    await onStatus("FAILED", pullRequestUrl);
    return "FAILED";
  }
}
