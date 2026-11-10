# Opportunity OS Build Orchestrator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Jonas's BYGG click create a durable, auditable build job that can autonomously implement, test, deploy, verify, and roll back supported targets, while failing closed on missing credentials, unknown cost, Shopify MAIN, or irreversible operations.

**Architecture:** n8n workflow 57 owns authorization, policy gates, job state, and Discord reporting. A small Railway worker service performs long-running coding/API work with Codex and target adapters. The worker never decides business policy; it receives an already-approved job and must obey hard technical gates before deployment.

**Tech Stack:** n8n, Railway, Node.js 20+, TypeScript, `@openai/codex-sdk`, git CLI, Vitest, GitHub API, n8n public API, Railway API, Shopify Admin/Theme API where credentials exist.

**Spec:** `docs/superpowers/specs/2026-09-19-opportunity-os-design.md`

## Global Constraints

- BYGG is valid only from Jonas Discord user ID `388380559606546432`.
- Default autonomous new external-service spend limit is 0 SEK/month.
- Unknown price blocks paid activation.
- Shopify MAIN is never published without a separate Jonas approval.
- Unsupported/unauthenticated target adapters stop at `BLOCKED_CAPABILITY`; they never fall back to guessed actions.
- Automated tests must pass before deployment.
- Post-deploy verification must pass or a defined rollback must run.
- Every side effect is idempotent by `job_id`.
- No secrets are stored in Data Tables, Discord, Notion, or GitHub files.
- The coding worker may write only inside the checked-out job workspace and only to the target repository/branch.
- Existing production workflows are not replaced until a verified replacement is live.

## Review Focus

1. Replayed Discord BUILD actions must not execute twice.
2. A missing token/API capability must stop before any partial deployment.
3. Shopify experiment-site work must never cross into MAIN without a second explicit approval.
4. Codex-generated code that passes unit tests but fails live health checks must roll back.
5. A job that claims 0 cost but discovers a paid dependency must stop at `WAITING_COST_APPROVAL`.

---

### Task 1: Create durable build-job state

**Objects:**
- Create Data Table: `GK_OS_BUILD_JOBS`

**Interfaces:**
- Consumes: `GK_OS_ACTIONS` BUILD rows.
- Produces: worker/job lifecycle state.

- [ ] **Step 1: Create the table with the exact schema**

```json
[
  {"name":"job_id","type":"string"},
  {"name":"opportunity_id","type":"string"},
  {"name":"action_key","type":"string"},
  {"name":"target_type","type":"string"},
  {"name":"target_ref","type":"string"},
  {"name":"status","type":"string"},
  {"name":"phase","type":"string"},
  {"name":"plan_json","type":"string"},
  {"name":"metric_plan_json","type":"string"},
  {"name":"rollback_json","type":"string"},
  {"name":"estimated_monthly_cost","type":"number"},
  {"name":"approved_monthly_cost","type":"number"},
  {"name":"shopify_main_required","type":"boolean"},
  {"name":"worker_run_id","type":"string"},
  {"name":"result_ref","type":"string"},
  {"name":"error","type":"string"},
  {"name":"started_at","type":"date"},
  {"name":"heartbeat_at","type":"date"},
  {"name":"finished_at","type":"date"},
  {"name":"updated_at","type":"date"}
]
```

- [ ] **Step 2: Define allowed statuses**

The workflow/worker may persist only:

```text
QUEUED
POLICY_CHECK
BLOCKED_CAPABILITY
WAITING_COST_APPROVAL
BUILDING
TESTING
READY_TO_DEPLOY
WAITING_SHOPIFY_MAIN
DEPLOYING
VERIFYING
SUCCEEDED
ROLLED_BACK
FAILED
```

- [ ] **Step 3: Define deterministic job ID**

```js
job_id = "JOB-" + sha256("BUILD:" + opportunity_id).slice(0,12)
```

One opportunity has at most one active BUILD job unless the previous job is FAILED/ROLLED_BACK and a new explicit BUILD action occurs after material plan change.

### Task 2: Create the worker repository and test harness

**Repository:**
- Create: `ulle73/golfkuponger-opportunity-worker`

**Files:**
- Create: `package.json`
- Create: `tsconfig.json`
- Create: `Dockerfile`
- Create: `src/server.ts`
- Create: `src/types.ts`
- Create: `src/auth.ts`
- Create: `src/policies.ts`
- Create: `src/job-runner.ts`
- Create: `src/codex-runner.ts`
- Create: `src/callback.ts`
- Create: `src/adapters/github.ts`
- Create: `src/adapters/n8n.ts`
- Create: `src/adapters/railway.ts`
- Create: `src/adapters/shopify.ts`
- Create: `tests/auth.test.ts`
- Create: `tests/policies.test.ts`
- Create: `tests/job-runner.test.ts`

**Interfaces:**
- HTTP `POST /v1/jobs` accepts a signed BuildJobRequest and returns 202.
- HTTP `GET /health` returns 200 only when the service process is healthy.
- Worker calls a signed n8n callback after each phase transition.

- [ ] **Step 1: Write worker request/response types**

```ts
export type TargetType = "github" | "n8n" | "railway" | "shopify";

export interface BuildJobRequest {
  jobId: string;
  opportunityId: string;
  targetType: TargetType;
  targetRef: string;
  plan: string[];
  metricPlan: Array<Record<string, unknown>>;
  estimatedMonthlyCost: number;
  approvedMonthlyCost: number;
  shopifyMainRequired: boolean;
  callbackUrl: string;
  callbackNonce: string;
}

export interface JobProgress {
  jobId: string;
  status: string;
  phase: string;
  resultRef?: string;
  error?: string;
  rollback?: Record<string, unknown>;
}
```

- [ ] **Step 2: Write failing HMAC authentication tests**

Test:
- correct signature -> accepted,
- modified body -> rejected,
- missing timestamp -> rejected,
- timestamp older than 5 minutes -> rejected.

Use `WORKER_HMAC_SECRET` only from environment.

- [ ] **Step 3: Implement HMAC verification**

Canonical signed payload:

```text
<unix_timestamp>.<raw_request_body>
```

Use SHA-256 HMAC and constant-time comparison.

- [ ] **Step 4: Write policy tests**

Required tests:
- `estimatedMonthlyCost > approvedMonthlyCost` -> WAITING_COST_APPROVAL.
- target `shopify` with `shopifyMainRequired=true` -> cannot enter DEPLOYING.
- unknown target -> BLOCKED_CAPABILITY.
- missing target credential -> BLOCKED_CAPABILITY.
- irreversible plan marker without rollback -> BLOCKED_CAPABILITY.

- [ ] **Step 5: Implement `evaluatePolicy()`**

```ts
export interface PolicyInput {
  targetType: TargetType;
  estimatedMonthlyCost: number;
  approvedMonthlyCost: number;
  shopifyMainRequired: boolean;
  hasCredential: boolean;
  hasRollback: boolean;
  irreversible: boolean;
}

export type PolicyDecision =
  | { allow: true }
  | { allow: false; status: "WAITING_COST_APPROVAL" | "WAITING_SHOPIFY_MAIN" | "BLOCKED_CAPABILITY"; reason: string };
```

- [ ] **Step 6: Implement server endpoints**

`POST /v1/jobs`:
1. verify HMAC,
2. validate schema,
3. return 409 if same job is already active,
4. queue job in-process,
5. return `202 {"accepted":true,"jobId":"..."}`.

`GET /health`:
`200 {"ok":true}`.

- [ ] **Step 7: Run unit tests**

Run:
```bash
npm test
```

Expected: all auth/policy/job-runner tests pass.

- [ ] **Step 8: Commit**

```bash
git add .
git commit -m "feat: scaffold Opportunity OS build worker"
```

### Task 3: Implement Codex repository execution

**Files:**
- Modify: `src/codex-runner.ts`
- Modify: `src/adapters/github.ts`
- Create: `tests/github-adapter.test.ts`

**Interfaces:**
- Consumes a repo target + build plan.
- Produces a branch/ref, test result, and rollback ref.

- [ ] **Step 1: Add `@openai/codex-sdk`**

Use the official Codex SDK server-side. Do not hard-code a model name; use the SDK/account default unless a verified environment configuration explicitly sets one.

- [ ] **Step 2: Implement GitHub workspace preparation**

For repository targets:
1. clone target repo using `GITHUB_TOKEN`,
2. checkout current target base branch,
3. capture base commit SHA as rollback ref,
4. create branch `opportunity-os/<opportunityId>`,
5. reject dirty/unexpected workspace state.

- [ ] **Step 3: Implement Codex prompt envelope**

The worker prompt must include:
- exact opportunity build plan,
- exact target repo/branch,
- instruction to inspect repo docs before changes,
- minimal-diff rule,
- no secret creation/exfiltration,
- required tests/build commands discovered from repository config,
- stop if required capability/credential is missing,
- no production/deploy action from Codex itself.

Codex writes only to the isolated workspace. Deployment stays in the adapter/policy layer.

- [ ] **Step 4: Add repository verification**

After Codex returns:
- inspect git diff,
- reject changes outside repository,
- run repository-native tests/build,
- reject if no change was produced for a code-build job,
- store changed files + test output summary.

- [ ] **Step 5: Push branch only after tests pass**

Push `opportunity-os/<opportunityId>`.

Return:
```ts
{
  branch: string,
  baseSha: string,
  headSha: string,
  changedFiles: string[],
  testsPassed: true
}
```

- [ ] **Step 6: Unit-test failed tests**

Use a fixture repo where Codex output is simulated and tests fail.

Expected: branch is not marked READY_TO_DEPLOY; no merge/deploy call occurs.

### Task 4: Implement target adapters with fail-closed credential discovery

**Files:**
- Modify: `src/adapters/github.ts`
- Modify: `src/adapters/n8n.ts`
- Modify: `src/adapters/railway.ts`
- Modify: `src/adapters/shopify.ts`
- Modify: `src/policies.ts`
- Create: `tests/adapters.test.ts`

**Interfaces:**
- Each adapter exposes `capabilities()`, `prepare()`, `deploy()`, `verify()`, `rollback()`.

- [ ] **Step 1: Define the common adapter interface**

```ts
export interface BuildAdapter {
  capabilities(): Promise<{ ready: boolean; reason?: string }>;
  prepare(job: BuildJobRequest): Promise<Record<string, unknown>>;
  deploy(job: BuildJobRequest, prepared: Record<string, unknown>): Promise<Record<string, unknown>>;
  verify(job: BuildJobRequest, deployed: Record<string, unknown>): Promise<{ ok: boolean; details: string }>;
  rollback(job: BuildJobRequest, rollback: Record<string, unknown>): Promise<{ ok: boolean; details: string }>;
}
```

- [ ] **Step 2: GitHub adapter capability gate**

Require `GITHUB_TOKEN`.

For code-only jobs, GitHub adapter may prepare/push a verified branch. Auto-merge to the production branch is allowed only when:
- repo release/deploy path is verified,
- required branch protections/tests pass,
- merge itself is the documented production trigger or is followed by a verified deploy adapter.

Otherwise return `BLOCKED_CAPABILITY` before merge.

- [ ] **Step 3: n8n adapter capability gate**

Require:
- `N8N_BASE_URL=https://n8n-production-91e6.up.railway.app`
- `N8N_API_KEY`.

The adapter must:
1. read existing workflow before modification,
2. store the full prior workflow/version metadata as rollback material,
3. create/update draft,
4. validate/test before activation where the API supports it,
5. activate only after validation,
6. restore prior version on failed verification.

If the public API cannot provide an equivalent validation/test path for a requested change, stop at BLOCKED_CAPABILITY rather than activating blindly.

- [ ] **Step 4: Railway adapter capability gate**

Require `RAILWAY_API_TOKEN`.

The adapter may deploy only an already-tested revision. It must capture the prior deployment ID, wait for the new deployment to reach SUCCESS, run health verification, and redeploy/restore the prior revision when verification fails.

- [ ] **Step 5: Shopify adapter capability gate**

Require:
- `SHOPIFY_STORE_DOMAIN`
- `SHOPIFY_ADMIN_ACCESS_TOKEN`
- configured experiment theme ID.

The adapter may update only the unpublished `experiment-site` theme automatically.

If the job requires MAIN:
- set `WAITING_SHOPIFY_MAIN`,
- return the tested experiment theme reference,
- do not call any publish-to-main operation.

- [ ] **Step 6: Test every missing-credential path**

Expected: each adapter returns not-ready with a specific reason and performs no write.

### Task 5: Create `57 OS – Build Orchestrator`

**Objects:**
- Create n8n workflow: `57 OS – Build Orchestrator`
- Uses: `GK_OS_ACTIONS`, `GK_OS_OPPORTUNITIES`, `GK_OS_BUILD_JOBS`

**Interfaces:**
- Consumes: pending BUILD actions.
- Produces: build jobs + signed worker dispatch + Discord status updates.

- [ ] **Step 1: Create inactive workflow with Manual Trigger and 5-minute Schedule Trigger**

Use standard OS production settings; timeout 120s.

- [ ] **Step 2: Select only valid BUILD actions**

Require:
- `entity_type="opportunity"`,
- `action="BUILD"`,
- `user_id="388380559606546432"`,
- `status="PENDING"`,
- matching stored opportunity.

Reject anything else with action `status="ERROR"`.

- [ ] **Step 3: Create deterministic job**

Map target type from stored opportunity target:
- GitHub repo/path -> `github`
- named n8n workflow -> `n8n`
- Railway service -> `railway`
- Shopify experiment-site/theme -> `shopify`
- otherwise -> job `BLOCKED_CAPABILITY`.

Persist job before worker call.

- [ ] **Step 4: Apply n8n-side cost gate**

Default `approved_monthly_cost=0`.

If `monthly_cost_est > 0` or pricing is unknown:
- set `WAITING_COST_APPROVAL`,
- do not dispatch worker,
- send Jonas a concise Discord status with cost/reason.

A later explicit cost approval may set `approved_monthly_cost` for this job only.

- [ ] **Step 5: Dispatch to worker with HMAC**

POST worker request with timestamp/signature. If worker returns 202:
- set `BUILDING`,
- store `worker_run_id` if returned,
- mark action `processed_at`.

If worker is unavailable, leave the job QUEUED with error and retry on next schedule using idempotent job ID.

- [ ] **Step 6: Add callback webhook**

Create a secret-path n8n webhook for worker callbacks.

Verify callback HMAC before updating `GK_OS_BUILD_JOBS`.

Allowed callback transitions must follow the status graph; reject impossible transitions such as `QUEUED -> SUCCEEDED`.

- [ ] **Step 7: Add stale-job recovery**

If `status` is BUILDING/TESTING/DEPLOYING/VERIFYING and `heartbeat_at` is older than 15 minutes:
- mark `FAILED` only after one worker status retry fails,
- preserve rollback/result refs,
- notify Jonas.

### Task 6: Implement separate Shopify MAIN approval

**Objects:**
- Modify workflow 55 publisher/status sender
- Modify workflow 56 Discord interactions
- Modify workflow 57 build orchestrator

**Interfaces:**
- Adds one build-result action visible only when a job is `WAITING_SHOPIFY_MAIN`.

- [ ] **Step 1: Add completion card**

```text
✅ Ändringen är byggd och testad i experiment-site.

Kontrollerna gick igenom och MAIN är fortfarande orörd.

[ PUBLICERA MAIN ] [ AVBRYT ] [ MER INFO ]
```

Custom IDs:
```text
osbuild:SHOPIFY_MAIN:<job_id>
osbuild:CANCEL:<job_id>
osbuildmore:<job_id>
```

- [ ] **Step 2: Extend signed Discord routing**

Only Jonas can trigger `SHOPIFY_MAIN` or `CANCEL`.

- [ ] **Step 3: Enforce second approval**

The original BUILD interaction ID must differ from the Shopify MAIN approval interaction ID.

Store both events.

### Task 7: Deploy worker to Railway

**Objects:**
- Create Railway service: `opportunity-os-worker`
- Source: `ulle73/golfkuponger-opportunity-worker`

**Environment variable names:**
```text
WORKER_HMAC_SECRET
OPENAI_API_KEY
GITHUB_TOKEN
N8N_BASE_URL
N8N_API_KEY
RAILWAY_API_TOKEN
SHOPIFY_STORE_DOMAIN
SHOPIFY_ADMIN_ACCESS_TOKEN
SHOPIFY_EXPERIMENT_THEME_ID
CALLBACK_HMAC_SECRET
```

No secret values are committed.

- [ ] **Step 1: Deploy with only non-secret config first**

The service must start and `GET /health` must return 200 even if adapters are not credential-ready.

- [ ] **Step 2: Add secrets through Railway environment management**

Never echo secret values into chat/logs.

- [ ] **Step 3: Run capability report**

The worker returns which adapters are READY vs BLOCKED without returning credential content.

- [ ] **Step 4: Enable workflow 57 only after at least one real adapter is READY**

If none is READY, keep 57 inactive and preserve BUILD actions in PENDING state rather than pretending the system can execute them.

### Task 8: End-to-end BUILD QA

- [ ] **Step 1: Use a reversible synthetic target**

Choose a non-production repository/test workflow designed for QA.

- [ ] **Step 2: Click BYGG as Jonas**

Expected: one action, one deterministic build job.

- [ ] **Step 3: Verify worker lifecycle**

Expected sequence:
`QUEUED -> POLICY_CHECK -> BUILDING -> TESTING -> READY_TO_DEPLOY -> DEPLOYING -> VERIFYING -> SUCCEEDED`.

- [ ] **Step 4: Replay the same Discord interaction payload**

Expected: no second job/deployment.

- [ ] **Step 5: Simulate verification failure**

Expected: rollback executes and final status is `ROLLED_BACK`, not SUCCEEDED.

- [ ] **Step 6: Test Shopify MAIN gate**

Expected: experiment-site change can reach WAITING_SHOPIFY_MAIN; MAIN remains untouched until separate Jonas action.

- [ ] **Step 7: Turn production execution saving off everywhere after QA**

Verify worker logs contain no secrets and n8n execution retention matches OS settings.
