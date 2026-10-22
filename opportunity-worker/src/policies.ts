import type { TargetType } from "./types.js";

export interface PolicyInput {
  targetType: TargetType;
  estimatedMonthlyCost: number;
  approvedMonthlyCost: number;
  shopifyMainRequired: boolean;
  hasCredential: boolean;
  hasRollback: boolean;
  irreversible: boolean;
  adapterImplemented: boolean;
}

export type PolicyDecision =
  | { allow: true }
  | { allow: false; status: "WAITING_COST_APPROVAL" | "WAITING_SHOPIFY_MAIN" | "BLOCKED_CAPABILITY"; reason: string };

export function evaluatePolicy(input: PolicyInput): PolicyDecision {
  if (input.estimatedMonthlyCost > input.approvedMonthlyCost) {
    return { allow: false, status: "WAITING_COST_APPROVAL", reason: "Ny kostnad över uttryckligt godkänd gräns." };
  }
  if (input.targetType === "shopify" && input.shopifyMainRequired) {
    return { allow: false, status: "WAITING_SHOPIFY_MAIN", reason: "Shopify MAIN kräver separat Jonas-godkännande." };
  }
  if (!input.adapterImplemented) {
    return { allow: false, status: "BLOCKED_CAPABILITY", reason: "Det finns ännu ingen verifierad produktionsadapter för targettypen." };
  }
  if (!input.hasCredential) {
    return { allow: false, status: "BLOCKED_CAPABILITY", reason: "Nödvändig credential saknas." };
  }
  if (input.irreversible && !input.hasRollback) {
    return { allow: false, status: "BLOCKED_CAPABILITY", reason: "Irreversibel ändring saknar verifierad rollback." };
  }
  return { allow: true };
}