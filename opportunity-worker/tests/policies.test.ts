import { describe, expect, it } from "vitest";
import { evaluatePolicy } from "../src/policies.js";

const base = {
  targetType: "github" as const,
  estimatedMonthlyCost: 0,
  approvedMonthlyCost: 0,
  shopifyMainRequired: false,
  hasCredential: true,
  hasRollback: true,
  irreversible: false,
  adapterImplemented: true,
};

describe("evaluatePolicy", () => {
  it("blocks spend above explicit approval", () => {
    expect(evaluatePolicy({...base, estimatedMonthlyCost: 1}).status).toBe("WAITING_COST_APPROVAL");
  });
  it("blocks Shopify MAIN for separate Jonas approval", () => {
    expect(evaluatePolicy({...base, targetType:"shopify", shopifyMainRequired:true}).status).toBe("WAITING_SHOPIFY_MAIN");
  });
  it("blocks missing credentials", () => {
    expect(evaluatePolicy({...base, hasCredential:false}).status).toBe("BLOCKED_CAPABILITY");
  });
  it("blocks irreversible work without rollback", () => {
    expect(evaluatePolicy({...base, irreversible:true, hasRollback:false}).status).toBe("BLOCKED_CAPABILITY");
  });
  it("blocks adapters that are not implemented", () => {
    expect(evaluatePolicy({...base, adapterImplemented:false}).status).toBe("BLOCKED_CAPABILITY");
  });
  it("allows a reversible, credential-ready, zero-cost build", () => {
    expect(evaluatePolicy(base)).toEqual({allow:true});
  });
});