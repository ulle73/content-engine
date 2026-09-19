import { createServer, type IncomingMessage, type Server, type ServerResponse } from "node:http";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { authorizeWorkerRequest, signHmac } from "./auth.js";
import { runGithubCodexBuild } from "./codex-runner.js";
import { createGitHubRefClient, finalizeGitHubBuild, type GitHubRefClient } from "./github-deploy.js";
import { evaluatePolicy } from "./policies.js";
import type {
  BuildJobRequest,
  CallbackJob,
  FinalizeJobRequest,
  GitHubRollbackMetadata,
  JobProgress,
  JobStatus,
  TargetType,
} from "./types.js";

export interface WorkerConfig {
  workerHmacSecret: string;
  callbackHmacSecret: string;
  allowPrivateUnsigned: boolean;
  publicDomain: string;
  githubToken: string;
  openAiApiKey: string;
  githubAutomergeRepos: string;
  githubAutodeployTargets: string;
  n8nApiKey: string;
  railwayApiToken: string;
  shopifyAdminAccessToken: string;
  shopifyExperimentThemeId: string;
}

export interface WorkerDependencies {
  runBuild?: typeof runGithubCodexBuild;
  githubClient?: GitHubRefClient;
  sendCallback?: (job: CallbackJob, progress: JobProgress) => Promise<void>;
}

function configFromProcess(): WorkerConfig {
  return {
    workerHmacSecret: process.env.WORKER_HMAC_SECRET || "",
    callbackHmacSecret: process.env.CALLBACK_HMAC_SECRET || process.env.WORKER_HMAC_SECRET || "",
    allowPrivateUnsigned: process.env.ALLOW_PRIVATE_UNSIGNED === "true",
    publicDomain: process.env.RAILWAY_PUBLIC_DOMAIN || "",
    githubToken: process.env.GITHUB_TOKEN || "",
    openAiApiKey: process.env.OPENAI_API_KEY || "",
    githubAutomergeRepos: process.env.GITHUB_AUTOMERGE_REPOS || "",
    githubAutodeployTargets: process.env.GITHUB_AUTODEPLOY_TARGETS || "",
    n8nApiKey: process.env.N8N_API_KEY || "",
    railwayApiToken: process.env.RAILWAY_API_TOKEN || "",
    shopifyAdminAccessToken: process.env.SHOPIFY_ADMIN_ACCESS_TOKEN || "",
    shopifyExperimentThemeId: process.env.SHOPIFY_EXPERIMENT_THEME_ID || "",
  };
}

function json(res: ServerResponse, status: number, responseBody: unknown) {
  const data = JSON.stringify(responseBody);
  res.writeHead(status, { "content-type": "application/json; charset=utf-8" });
  res.end(data);
}

async function body(req: IncomingMessage): Promise<string> {
  const chunks: Buffer[] = [];
  for await (const chunk of req) chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  return Buffer.concat(chunks).toString("utf8");
}

function credentialReady(target: TargetType, config: WorkerConfig): boolean {
  if (target === "github") return Boolean(config.githubToken && config.openAiApiKey);
  if (target === "n8n") return Boolean(config.n8nApiKey);
  if (target === "railway") return Boolean(config.railwayApiToken);
  if (target === "shopify") return Boolean(config.shopifyAdminAccessToken && config.shopifyExperimentThemeId);
  return false;
}

function adapterImplemented(target: TargetType): boolean {
  return target === "github";
}

async function callback(config: WorkerConfig, job: CallbackJob, progress: JobProgress) {
  if (!config.callbackHmacSecret || !job.callbackUrl) return;
  const payload = JSON.stringify({ ...progress, callbackNonce: job.callbackNonce });
  const timestamp = String(Math.floor(Date.now() / 1000));
  const signature = signHmac(config.callbackHmacSecret, timestamp, payload);
  await fetch(job.callbackUrl, {
    method: "POST",
    headers: { "content-type": "application/json", "x-os-timestamp": timestamp, "x-os-signature": signature },
    body: payload,
  }).catch(() => undefined);
}

function parseTargetRef(targetRef: string): { repo: string; branch: string } | undefined {
  const separator = targetRef.indexOf("@");
  if (separator <= 0 || separator !== targetRef.lastIndexOf("@")) return undefined;
  const repo = targetRef.slice(0, separator);
  const branch = targetRef.slice(separator + 1);
  if (!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repo)) return undefined;
  if (!/^[A-Za-z0-9_./-]+$/.test(branch)) return undefined;
  return { repo, branch };
}

function validRollback(value: unknown, targetRef: string): value is GitHubRollbackMetadata {
  if (!value || typeof value !== "object") return false;
  const rollback = value as Record<string, unknown>;
  const target = parseTargetRef(targetRef);
  if (!target) return false;
  if (rollback.repo !== target.repo || rollback.branch !== target.branch) return false;
  if (typeof rollback.baseSha !== "string" || !/^[a-f0-9]{40,64}$/i.test(rollback.baseSha)) return false;
  if (typeof rollback.headSha !== "string" || !/^[a-f0-9]{40,64}$/i.test(rollback.headSha)) return false;
  if (rollback.baseSha === rollback.headSha) return false;
  return typeof rollback.workBranch === "string" && /^[A-Za-z0-9_./-]+$/.test(rollback.workBranch);
}

function validFinalizeJob(value: unknown): value is FinalizeJobRequest {
  if (!value || typeof value !== "object") return false;
  const job = value as Record<string, unknown>;
  return typeof job.jobId === "string" && Boolean(job.jobId)
    && job.targetType === "github"
    && typeof job.targetRef === "string"
    && typeof job.callbackUrl === "string" && Boolean(job.callbackUrl)
    && typeof job.callbackNonce === "string" && Boolean(job.callbackNonce)
    && validRollback(job.rollback, job.targetRef);
}

function finalizationPhase(status: JobStatus): string {
  if (status === "DEPLOYING") return "github_pull_request_ready";
  if (status === "VERIFYING") return "target_ref_updated";
  if (status === "SUCCEEDED") return "finalization_succeeded";
  if (status === "ROLLED_BACK") return "finalization_rolled_back";
  return "finalization_failed";
}

export function createWorkerServer(config: WorkerConfig, dependencies: WorkerDependencies = {}): Server {
  const active = new Set<string>();
  const sendCallback: NonNullable<WorkerDependencies["sendCallback"]> = dependencies.sendCallback
    || ((job, progress) => callback(config, job, progress));

  async function executeBuild(job: BuildJobRequest) {
    try {
      await sendCallback(job, { jobId: job.jobId, status: "BUILDING", phase: "worker_started" });
      if (job.targetType !== "github") throw new Error("Adapter not implemented");
      const result = await (dependencies.runBuild || runGithubCodexBuild)(job);
      await sendCallback(job, {
        jobId: job.jobId,
        status: "READY_TO_DEPLOY",
        phase: "repository_tests_passed",
        resultRef: result.resultRef,
        rollback: result.rollback,
      });
    } catch (error) {
      await sendCallback(job, {
        jobId: job.jobId,
        status: "FAILED",
        phase: "worker_failed",
        error: error instanceof Error ? error.message.slice(0, 2000) : String(error).slice(0, 2000),
      });
    } finally {
      active.delete(job.jobId);
    }
  }

  async function executeFinalize(job: FinalizeJobRequest) {
    try {
      const client = dependencies.githubClient || createGitHubRefClient(config.githubToken);
      await finalizeGitHubBuild({
        client,
        ...job.rollback,
        allowTargets: config.githubAutodeployTargets,
        onStatus: async (status, resultRef, error) => {
          await sendCallback(job, {
            jobId: job.jobId,
            status,
            phase: finalizationPhase(status),
            ...(resultRef ? { resultRef } : {}),
            ...(status === "FAILED" && error ? { error } : {}),
          });
        },
      });
    } catch (error) {
      await sendCallback(job, {
        jobId: job.jobId,
        status: "FAILED",
        phase: "finalization_failed",
        error: error instanceof Error ? error.message.slice(0, 2000) : String(error).slice(0, 2000),
      });
    } finally {
      active.delete(job.jobId);
    }
  }

  return createServer(async (req, res) => {
    if (req.method === "GET" && req.url === "/health") return json(res, 200, { ok: true });
    if (req.method === "GET" && req.url === "/v1/capabilities") {
      return json(res, 200, {
        github: {
          implemented: true,
          credentialReady: credentialReady("github", config),
          productionAllowlistConfigured: Boolean(config.githubAutomergeRepos),
          autoDeployTargetsConfigured: Boolean(config.githubAutodeployTargets.trim()),
          privateUnsignedDispatch: config.allowPrivateUnsigned && !config.publicDomain,
        },
        n8n: { implemented: false, credentialReady: credentialReady("n8n", config) },
        railway: { implemented: false, credentialReady: credentialReady("railway", config) },
        shopify: {
          implemented: false,
          credentialReady: credentialReady("shopify", config),
          mainAlwaysRequiresSeparateApproval: true,
        },
      });
    }
    if (req.method !== "POST" || (req.url !== "/v1/jobs" && req.url !== "/v1/finalize")) {
      return json(res, 404, { error: "not_found" });
    }

    const raw = await body(req);
    const authorized = authorizeWorkerRequest({
      secret: config.workerHmacSecret,
      timestamp: String(req.headers["x-os-timestamp"] || ""),
      body: raw,
      signature: String(req.headers["x-os-signature"] || ""),
      allowPrivateUnsigned: config.allowPrivateUnsigned,
      publicDomain: config.publicDomain,
    });
    if (!authorized) return json(res, 401, { error: "invalid_signature" });

    let parsed: unknown;
    try {
      parsed = JSON.parse(raw);
    } catch {
      return json(res, 400, { error: "invalid_json" });
    }

    if (req.url === "/v1/finalize") {
      if (!validFinalizeJob(parsed)) return json(res, 400, { error: "invalid_job" });
      if (active.has(parsed.jobId)) return json(res, 409, { error: "job_active" });
      active.add(parsed.jobId);
      void executeFinalize(parsed);
      return json(res, 202, { accepted: true, jobId: parsed.jobId, status: "DEPLOYING" });
    }

    if (!parsed || typeof parsed !== "object") return json(res, 400, { error: "invalid_job" });
    const job = parsed as BuildJobRequest;
    if (!job.jobId || active.has(job.jobId)) {
      return json(res, active.has(job.jobId) ? 409 : 400, {
        error: active.has(job.jobId) ? "job_active" : "invalid_job",
      });
    }

    const decision = evaluatePolicy({
      targetType: job.targetType,
      estimatedMonthlyCost: Number(job.estimatedMonthlyCost || 0),
      approvedMonthlyCost: Number(job.approvedMonthlyCost || 0),
      shopifyMainRequired: Boolean(job.shopifyMainRequired),
      hasCredential: credentialReady(job.targetType, config),
      hasRollback: job.targetType === "github",
      irreversible: false,
      adapterImplemented: adapterImplemented(job.targetType),
    });
    if (!decision.allow) {
      await sendCallback(job, { jobId: job.jobId, status: decision.status, phase: "policy_block", error: decision.reason });
      return json(res, 202, {
        accepted: false,
        jobId: job.jobId,
        status: decision.status,
        reason: decision.reason,
      });
    }

    active.add(job.jobId);
    void executeBuild(job);
    return json(res, 202, { accepted: true, jobId: job.jobId, status: "BUILDING" });
  });
}

if (fileURLToPath(import.meta.url) === resolve(process.argv[1] || "")) {
  const server = createWorkerServer(configFromProcess());
  const port = Number(process.env.PORT || 3000);
  server.listen(port, "0.0.0.0", () => console.log(`Opportunity OS worker listening on :${port}`));
}
