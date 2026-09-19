export type TargetType = "github" | "n8n" | "railway" | "shopify";
export type JobStatus =
  | "QUEUED" | "POLICY_CHECK" | "BLOCKED_CAPABILITY" | "WAITING_COST_APPROVAL"
  | "BUILDING" | "TESTING" | "READY_TO_DEPLOY" | "WAITING_SHOPIFY_MAIN"
  | "DEPLOYING" | "VERIFYING" | "SUCCEEDED" | "ROLLED_BACK" | "FAILED";

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
  status: JobStatus;
  phase: string;
  resultRef?: string;
  error?: string;
  rollback?: Record<string, unknown>;
}