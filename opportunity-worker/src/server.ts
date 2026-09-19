import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import { signHmac, verifyHmac } from "./auth.js";
import { evaluatePolicy } from "./policies.js";
import { runGithubCodexBuild } from "./codex-runner.js";
import type { BuildJobRequest, JobProgress, TargetType } from "./types.js";

const active = new Set<string>();

function json(res: ServerResponse, status: number, body: unknown) {
  const data = JSON.stringify(body);
  res.writeHead(status, { "content-type": "application/json; charset=utf-8" });
  res.end(data);
}

async function body(req: IncomingMessage): Promise<string> {
  const chunks: Buffer[] = [];
  for await (const chunk of req) chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  return Buffer.concat(chunks).toString("utf8");
}

function credentialReady(target: TargetType): boolean {
  if (target === "github") return Boolean(process.env.GITHUB_TOKEN && process.env.OPENAI_API_KEY);
  if (target === "n8n") return Boolean(process.env.N8N_API_KEY);
  if (target === "railway") return Boolean(process.env.RAILWAY_API_TOKEN);
  if (target === "shopify") return Boolean(process.env.SHOPIFY_ADMIN_ACCESS_TOKEN && process.env.SHOPIFY_EXPERIMENT_THEME_ID);
  return false;
}

function adapterImplemented(target: TargetType): boolean {
  return target === "github";
}

async function callback(job: BuildJobRequest, progress: JobProgress) {
  const secret = process.env.CALLBACK_HMAC_SECRET || process.env.WORKER_HMAC_SECRET || "";
  if (!secret || !job.callbackUrl) return;
  const payload = JSON.stringify({ ...progress, callbackNonce: job.callbackNonce });
  const ts = String(Math.floor(Date.now() / 1000));
  const sig = signHmac(secret, ts, payload);
  await fetch(job.callbackUrl, {
    method: "POST",
    headers: { "content-type": "application/json", "x-os-timestamp": ts, "x-os-signature": sig },
    body: payload,
  }).catch(() => undefined);
}

async function execute(job: BuildJobRequest) {
  active.add(job.jobId);
  try {
    await callback(job, { jobId: job.jobId, status: "BUILDING", phase: "worker_started" });
    if (job.targetType !== "github") throw new Error("Adapter not implemented");
    const result = await runGithubCodexBuild(job);
    await callback(job, { jobId: job.jobId, status: "READY_TO_DEPLOY", phase: "repository_tests_passed", resultRef: result.resultRef, rollback: result.rollback });
  } catch (e) {
    await callback(job, { jobId: job.jobId, status: "FAILED", phase: "worker_failed", error: e instanceof Error ? e.message.slice(0, 2000) : String(e).slice(0, 2000) });
  } finally {
    active.delete(job.jobId);
  }
}

const server = createServer(async (req, res) => {
  if (req.method === "GET" && req.url === "/health") return json(res, 200, { ok: true });
  if (req.method === "GET" && req.url === "/v1/capabilities") {
    return json(res, 200, {
      github: { implemented: true, credentialReady: credentialReady("github"), productionAllowlistConfigured: Boolean(process.env.GITHUB_AUTOMERGE_REPOS) },
      n8n: { implemented: false, credentialReady: credentialReady("n8n") },
      railway: { implemented: false, credentialReady: credentialReady("railway") },
      shopify: { implemented: false, credentialReady: credentialReady("shopify"), mainAlwaysRequiresSeparateApproval: true },
    });
  }
  if (req.method !== "POST" || req.url !== "/v1/jobs") return json(res, 404, { error: "not_found" });

  const raw = await body(req);
  const secret = process.env.WORKER_HMAC_SECRET || "";
  if (!verifyHmac({ secret, timestamp: String(req.headers["x-os-timestamp"] || ""), body: raw, signature: String(req.headers["x-os-signature"] || "") })) {
    return json(res, 401, { error: "invalid_signature" });
  }

  let job: BuildJobRequest;
  try { job = JSON.parse(raw) as BuildJobRequest; } catch { return json(res, 400, { error: "invalid_json" }); }
  if (!job.jobId || active.has(job.jobId)) return json(res, active.has(job.jobId) ? 409 : 400, { error: active.has(job.jobId) ? "job_active" : "invalid_job" });

  const decision = evaluatePolicy({
    targetType: job.targetType,
    estimatedMonthlyCost: Number(job.estimatedMonthlyCost || 0),
    approvedMonthlyCost: Number(job.approvedMonthlyCost || 0),
    shopifyMainRequired: Boolean(job.shopifyMainRequired),
    hasCredential: credentialReady(job.targetType),
    hasRollback: job.targetType === "github",
    irreversible: false,
    adapterImplemented: adapterImplemented(job.targetType),
  });
  if (!decision.allow) {
    await callback(job, { jobId: job.jobId, status: decision.status, phase: "policy_block", error: decision.reason });
    return json(res, 202, { accepted: false, jobId: job.jobId, status: decision.status, reason: decision.reason });
  }

  void execute(job);
  return json(res, 202, { accepted: true, jobId: job.jobId, status: "BUILDING" });
});

const port = Number(process.env.PORT || 3000);
server.listen(port, "0.0.0.0", () => console.log(`Opportunity OS worker listening on :${port}`));