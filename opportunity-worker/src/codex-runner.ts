import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, rmSync } from "node:fs";
import path from "node:path";
import { Codex } from "@openai/codex-sdk";
import type { BuildJobRequest } from "./types.js";

function run(cmd: string, args: string[], cwd: string, env: NodeJS.ProcessEnv = process.env): string {
  try {
    return execFileSync(cmd, args, { cwd, env, encoding: "utf8", timeout: 10 * 60 * 1000, stdio: ["ignore", "pipe", "pipe"] });
  } catch (error) {
    const e = error as { stderr?: Buffer | string; stdout?: Buffer | string; message?: string };
    const stderr = String(e.stderr ?? "").slice(-4000);
    const stdout = String(e.stdout ?? "").slice(-2000);
    throw new Error(("Command failed. " + stderr + " " + stdout).trim());
  }
}

function parseRepo(ref: string): { repo: string; branch: string } {
  const [repo, branch = "main"] = ref.split("@");
  if (!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repo)) throw new Error("Invalid GitHub target_ref");
  if (!/^[A-Za-z0-9_./-]+$/.test(branch)) throw new Error("Invalid GitHub branch");
  return { repo, branch };
}

export async function runGithubCodexBuild(job: BuildJobRequest): Promise<{ resultRef: string; rollback: Record<string, unknown> }> {
  const token = process.env.GITHUB_TOKEN ?? "";
  const apiKey = process.env.OPENAI_API_KEY ?? "";
  if (!token || !apiKey) throw new Error("Missing GitHub/OpenAI credential");
  const { repo, branch } = parseRepo(job.targetRef);
  const allow = new Set((process.env.GITHUB_AUTOMERGE_REPOS ?? "").split(",").map(s => s.trim()).filter(Boolean));
  if (!allow.has(repo)) throw new Error("Repository is not in GITHUB_AUTOMERGE_REPOS; production path is not verified");

  const root = process.env.WORK_ROOT || "/tmp/opportunity-os";
  const dir = path.join(root, job.jobId);
  rmSync(dir, { recursive: true, force: true });
  mkdirSync(root, { recursive: true });

  const cloneUrl = `https://x-access-token:${encodeURIComponent(token)}@github.com/${repo}.git`;
  run("git", ["clone", "--depth", "20", "--branch", branch, cloneUrl, dir], root);
  const baseSha = run("git", ["rev-parse", "HEAD"], dir).trim();
  const workBranch = `opportunity-os/${job.opportunityId.toLowerCase()}`;
  run("git", ["checkout", "-b", workBranch], dir);
  run("git", ["config", "user.email", "opportunity-os@golfkuponger.se"], dir);
  run("git", ["config", "user.name", "Golfkuponger Opportunity OS"], dir);

  const codex = new Codex({ apiKey });
  const thread = codex.startThread({
    workingDirectory: dir,
    sandboxMode: "workspace-write",
    approvalPolicy: "never",
    networkAccessEnabled: false,
    modelReasoningEffort: "high",
  });
  const prompt = [
    "Implementera endast den godkända Golfkuponger-planen nedan.",
    "Läs repo-dokumentation och befintliga mönster först.",
    "Gör minsta kompletta diff. Ändra inte secrets, deployment-konfiguration eller andra projekt.",
    "Kör relevanta lokala tester om repo-dokumentationen anger dem.",
    "Om planen kräver credentials, externa system eller fakta du inte kan verifiera: stoppa utan att gissa.",
    "",
    ...job.plan.map((s, i) => `${i + 1}. ${s}`),
  ].join("\n");
  const turn = await thread.run(prompt);

  if (existsSync(path.join(dir, "package.json"))) {
    run("npm", ["test", "--if-present"], dir);
    run("npm", ["run", "build", "--if-present"], dir);
  }
  const status = run("git", ["status", "--porcelain"], dir).trim();
  if (!status) {\n    const detail = String(turn.finalResponse || "").trim().slice(-1500);\n    throw new Error(`Codex produced no repository change${detail ? `: ${detail}` : ""}`);\n  }
  run("git", ["add", "-A"], dir);
  run("git", ["commit", "-m", `feat: Opportunity OS ${job.opportunityId}`], dir);
  const headSha = run("git", ["rev-parse", "HEAD"], dir).trim();
  run("git", ["push", "-u", "origin", workBranch], dir);

  // Production merge/deploy is deliberately not guessed. The allowlist proves only that
  // repository writes are approved; n8n must still have a verified production adapter.
  return {
    resultRef: `https://github.com/${repo}/tree/${workBranch}`,
    rollback: { repo, branch, baseSha, headSha, workBranch },
  };
}