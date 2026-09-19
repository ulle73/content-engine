export interface GitHubRefClient {
  getRef(repo: string, branch: string): Promise<string>;
  setRef(repo: string, branch: string, sha: string): Promise<void>;
  restoreRef(repo: string, branch: string, sha: string): Promise<void>;
}

type RequestFn = typeof fetch;

function refUrl(repo: string, branch: string): string {
  const [owner, name] = repo.split("/");
  if (!owner || !name) throw new Error("Invalid GitHub repository");
  return `https://api.github.com/repos/${encodeURIComponent(owner)}/${encodeURIComponent(name)}/git/ref/heads/${encodeURIComponent(branch)}`;
}

export function createGitHubRefClient(token: string, request: RequestFn = fetch): GitHubRefClient {
  if (!token) throw new Error("Missing GITHUB_TOKEN");

  async function call(repo: string, branch: string, init?: RequestInit): Promise<any> {
    const response = await request(refUrl(repo, branch), {
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
      throw new Error(`GitHub refs API failed (${response.status}): ${detail}`);
    }
    return response.json();
  }

  return {
    async getRef(repo, branch) {
      const data = await call(repo, branch, { method: "GET" });
      const sha = String(data?.object?.sha || "");
      if (!sha) throw new Error("GitHub ref response did not contain a SHA");
      return sha;
    },
    async setRef(repo, branch, sha) {
      await call(repo, branch, { method: "PATCH", body: JSON.stringify({ sha, force: false }) });
    },
    async restoreRef(repo, branch, sha) {
      await call(repo, branch, { method: "PATCH", body: JSON.stringify({ sha, force: true }) });
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
}) {
  const { client, repo, branch, baseSha, headSha } = args;
  const current = await client.getRef(repo, branch);
  if (current !== baseSha) {
    throw new Error("Target branch moved after build started");
  }
  await client.setRef(repo, branch, headSha);
  const verified = await client.getRef(repo, branch);
  if (verified !== headSha) {
    throw new Error("Deployed revision verification failed");
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
