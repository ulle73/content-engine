import { createHmac, timingSafeEqual } from "node:crypto";

export function verifyHmac(args: {
  secret: string;
  timestamp: string;
  body: string;
  signature: string;
  nowMs?: number;
}): boolean {
  const { secret, timestamp, body, signature } = args;
  if (!secret || !timestamp || !signature) return false;
  const ts = Number(timestamp);
  if (!Number.isFinite(ts)) return false;
  const nowMs = args.nowMs ?? Date.now();
  if (Math.abs(nowMs - ts * 1000) > 5 * 60 * 1000) return false;
  const expected = createHmac("sha256", secret).update(timestamp + "." + body).digest("hex");
  if (expected.length !== signature.length) return false;
  return timingSafeEqual(Buffer.from(expected, "hex"), Buffer.from(signature, "hex"));
}

export function authorizeWorkerRequest(args: {
  secret: string;
  timestamp: string;
  body: string;
  signature: string;
  allowPrivateUnsigned: boolean;
  publicDomain: string;
  nowMs?: number;
}): boolean {
  if (verifyHmac(args)) return true;
  return args.allowPrivateUnsigned && !args.publicDomain;
}

export function signHmac(secret: string, timestamp: string, body: string): string {
  return createHmac("sha256", secret).update(timestamp + "." + body).digest("hex");
}