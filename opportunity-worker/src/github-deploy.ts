export interface GitHubRefClient {
  getRef(repo: string, branch: string): Promise<string>;
  setRef(repo: string, branch: string, sha: string): Promise<void>;
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
