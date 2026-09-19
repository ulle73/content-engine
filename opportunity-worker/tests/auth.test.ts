import { createHmac } from "node:crypto";
import { describe, expect, it } from "vitest";
import { verifyHmac } from "../src/auth.js";

const secret="test-secret";
function signature(ts:string,body:string){return createHmac("sha256",secret).update(ts+"."+body).digest("hex");}

describe("verifyHmac",()=>{
  it("accepts a valid signature",()=>{const ts=String(Math.floor(Date.now()/1000)); const body='{"ok":true}'; expect(verifyHmac({secret,timestamp:ts,body,signature:signature(ts,body),nowMs:Date.now()})).toBe(true);});
  it("rejects a modified body",()=>{const ts=String(Math.floor(Date.now()/1000)); const body='{"ok":true}'; expect(verifyHmac({secret,timestamp:ts,body:'{"ok":false}',signature:signature(ts,body),nowMs:Date.now()})).toBe(false);});
  it("rejects an old timestamp",()=>{const old=String(Math.floor((Date.now()-6*60*1000)/1000)); const body='{}'; expect(verifyHmac({secret,timestamp:old,body,signature:signature(old,body),nowMs:Date.now()})).toBe(false);});
});