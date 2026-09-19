import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, rmSync, statSync } from "node:fs";
import path from "node:path";
import { Codex } from "@openai/codex-sdk";
import { resolveModelAttempts, type LlmAttempt } from "./model-routing.js";
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

function gitAuthConfig(token: string): string {
  const basic = Buffer.from(`x-access-token:${token}`, "utf8").toString("base64");
  return `http.extraHeader=Authorization: Basic ${basic}`;
}

function prepareWorkspaceForCodex(dir: string, codexHome: string): void {
  mkdirSync(codexHome, { recursive: true });
  run("chown", ["-R", "10001:10001", dir], path.dirname(dir));
  run("chown", ["-R", "0:0", path.join(dir, ".git")], dir);
  run("chmod", ["-R", "go-w", path.join(dir, ".git")], dir);
  run("chown", ["0:10001", dir], path.dirname(dir));
  run("chmod", ["1775", dir], path.dirname(dir));
  run("chown", ["-R", "10001:10001", codexHome], path.dirname(codexHome));
}

function ensureNoSecretLeak(dir: string, secrets: string[]): void {
  const changed = run("git", ["diff", "--cached", "--name-only", "-z"], dir)
    .split("\0")
    .filter(Boolean);
  const root = path.resolve(dir) + path.sep;

  for (const relativePath of changed) {
    const fullPath = path.resolve(dir, relativePath);
    if (!fullPath.startsWith(root)) throw new Error("Changed file escaped repository root");
    if (!existsSync(fullPath) || !statSync(fullPath).isFile()) continue;

    const bytes = readFileSync(fullPath);
    for (const secret of secrets.filter(value => value.length >= 8)) {
      if (bytes.includes(Buffer.from(secret, "utf8"))) {
        throw new Error(`Secret-like credential detected in changed file: ${relativePath}`);
      }
    }
  }
}

function codexEnv(codexHome: string, extra: Record<string, string> = {}): Record<string, string> {
  return {
    PATH: process.env.PATH || "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    HOME: codexHome,
    TMPDIR: codexHome,
    USER: "codex",
    LOGNAME: "codex",
    LANG: process.env.LANG || "C.UTF-8",
    ...extra,
  };
}

function shellEnvironmentPolicy(): Record<string, string | boolean | string[]> {
  return {
    inherit: "core",
    ignore_default_excludes: false,
    include_only: ["PATH", "HOME", "TMPDIR", "USER", "LOGNAME", "LANG"],
  };
}

function createCodex(attempt: LlmAttempt, codexHome: string): Codex {
  return new Codex({
    codexPathOverride: "/usr/local/bin/codex-unprivileged",
    env: codexEnv(codexHome, { OPENROUTER_API_KEY: attempt.apiKey }),
    config: {
      model_provider: "openrouter",
      model_providers: {
        openrouter: {
          name: "OpenRouter",
          base_url: "https://openrouter.ai/api/v1",
          env_key: "OPENROUTER_API_KEY",
          wire_api: "responses",
          supports_websockets: false,
        },
      },
      shell_environment_policy: shellEnvironmentPolicy(),
    },
  });
}

function assertWorkspaceIntegrity(dir: string, workBranch: string, baseSha: string, cloneUrl: string): void {
  const currentBranch = run("git", ["branch", "--show-current"], dir).trim();
  const currentHead = run("git", ["rev-parse", "HEAD"], dir).trim();
  const currentRemote = run("git", ["remote", "get-url", "origin"], dir).trim();
  if (currentBranch !== workBranch) throw new Error("Codex changed the worker branch");
  if (currentHead !== baseSha) throw new Error("Codex changed Git history");
  if (currentRemote !== cloneUrl) throw new Error("Codex changed the Git remote");
}

function resetWorkspace(dir: string, baseSha: string): void {
  run("git", ["reset", "--hard", baseSha], dir);
  run("git", ["clean", "-fdx"], dir);
}

function errorDetail(error: unknown): string {
  return (error instanceof Error ? error.message : String(error)).trim().slice(-1800);
}

export async function runGithubCodexBuild(job: BuildJobRequest): Promise<{ resultRef: string; rollback: Record<string, unknown> }> {
  const token = (process.env.GITHUB_TOKEN ?? "").trim();
  const modelTier = job.modelTier ?? "free";
  const attempts = resolveModelAttempts(modelTier);
  if (!token || attempts.length === 0) throw new Error("Missing GitHub/OpenRouter credential");
  const { repo, branch } = parseRepo(job.targetRef);
  const allow = new Set((process.env.GITHUB_AUTOMERGE_REPOS ?? "").split(",").map(s => s.trim()).filter(Boolean));
  if (!allow.has(repo)) throw new Error("Repository is not in GITHUB_AUTOMERGE_REPOS; production path is not verified");

  const root = process.env.WORK_ROOT || "/tmp/opportunity-os";
  const dir = path.join(root, job.jobId);
  rmSync(dir, { recursive: true, force: true });
  mkdirSync(root, { recursive: true });

  const cloneUrl = `https://github.com/${repo}.git`;
  const authConfig = gitAuthConfig(token);
  run("git", ["-c", authConfig, "clone", "--depth", "20", "--branch", branch, cloneUrl, dir], root);
  const baseSha = run("git", ["rev-parse", "HEAD"], dir).trim();
  const workBranch = `opportunity-os/${job.opportunityId.toLowerCase()}`;
  run("git", ["checkout", "-b", workBranch], dir);
  run("git", ["config", "user.email", "opportunity-os@golfkuponger.se"], dir);
  run("git", ["config", "user.name", "Golfkuponger Opportunity OS"], dir);

  const prompt = [
    "Implementera endast den godkända Golfkuponger-planen nedan.",
    "Läs repo-dokumentation och befintliga mönster först.",
    "Gör minsta kompletta diff. Ändra inte secrets, deployment-konfiguration, .git, git-historik eller andra projekt.",
    "Använd inte nätverk eller externa tjänster. Läs inte processmiljö, /proc, credentials, tokens eller andra hemligheter.",
    "Kör relevanta lokala tester om repo-dokumentationen anger dem.",
    "Om planen kräver credentials, externa system eller fakta du inte kan verifiera: stoppa utan att gissa.",
    "",
    ...job.plan.map((s, i) => `${i + 1}. ${s}`),
  ].join("\n");

  const providerErrors: string[] = [];
  let selectedAttempt: LlmAttempt | undefined;

  for (const [index, attempt] of attempts.entries()) {
    if (index > 0) resetWorkspace(dir, baseSha);
    const codexHome = path.join(root, `${job.jobId}-${index}-${attempt.provider}-codex-home`);
    rmSync(codexHome, { recursive: true, force: true });
    prepareWorkspaceForCodex(dir, codexHome);

    try {
      const codex = createCodex(attempt, codexHome);
      const thread = codex.startThread({
        workingDirectory: dir,
        sandboxMode: "danger-full-access",
        approvalPolicy: "never",
        model: attempt.model,
        modelReasoningEffort: "high",
      });
      const turn = await thread.run(prompt);

      assertWorkspaceIntegrity(dir, workBranch, baseSha, cloneUrl);
      if (existsSync(path.join(dir, "package.json"))) {
        run("npm", ["test", "--if-present"], dir);
        run("npm", ["run", "build", "--if-present"], dir);
      }
      const status = run("git", ["status", "--porcelain"], dir).trim();
      if (!status) {
        const detail = String(turn.finalResponse || "").trim().slice(-1500);
        throw new Error(`Codex produced no repository change${detail ? `: ${detail}` : ""}`);
      }

      selectedAttempt = attempt;
      break;
    } catch (error) {
      // Only the free tier can fall back automatically; paid tiers contain one explicit model.
      assertWorkspaceIntegrity(dir, workBranch, baseSha, cloneUrl);
      providerErrors.push(`${attempt.provider}/${attempt.model}: ${errorDetail(error)}`);
    }
  }

  if (!selectedAttempt) {
    throw new Error(`All configured LLM providers failed. ${providerErrors.join(" | ")}`.slice(-5000));
  }

  run("git", ["add", "-A"], dir);
  ensureNoSecretLeak(dir, [
    token,
    ...attempts.map(attempt => attempt.apiKey),
    process.env.CALLBACK_HMAC_SECRET ?? "",
    process.env.WORKER_HMAC_SECRET ?? "",
  ]);
  run("git", ["commit", "-m", `feat: Opportunity OS ${job.opportunityId}`], dir);
  const headSha = run("git", ["rev-parse", "HEAD"], dir).trim();
  run("git", ["-c", authConfig, "push", "-u", "origin", workBranch], dir);

  // Production merge/deploy is deliberately not guessed. This worker only
  // creates and pushes a separate branch; n8n owns any later deploy decision.
  return {
    resultRef: `https://github.com/${repo}/tree/${workBranch}`,
    rollback: {
      repo,
      branch,
      baseSha,
      headSha,
      workBranch,
      requestedModelTier: modelTier,
      llmProvider: selectedAttempt.provider,
      llmModel: selectedAttempt.model,
    },
  };
}
