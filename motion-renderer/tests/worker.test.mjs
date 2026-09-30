import test from "node:test";
import assert from "node:assert/strict";
import { existsSync } from "node:fs";

test("worker protocol implementation exists", () => {
  assert.ok(
    existsSync(new URL("../worker-protocol.mjs", import.meta.url)),
    "worker protocol missing",
  );
});

test("configuration rejects credential-bearing URLs and implicit insecure HTTP", async () => {
  const { configuration } = await import("../worker-protocol.mjs");
  const env = {
    MOTION_API_URL: "https://content.example",
    MOTION_WORKER_TOKEN: "x".repeat(40),
    MOTION_LICENSE_MODE: "evaluation",
  };
  assert.equal(configuration(env).origin, "https://content.example");
  for (const url of [
    "http://content.example",
    "https://user:pass@content.example",
    "https://content.example/path?secret=x",
    "file:///etc/passwd",
  ]) {
    assert.throws(() => configuration({ ...env, MOTION_API_URL: url }));
  }
  assert.throws(() => configuration({ ...env, MOTION_WORKER_TOKEN: "short" }));
  assert.throws(() => configuration({ ...env, MOTION_LICENSE_MODE: "" }));
  assert.equal(
    configuration({
      ...env,
      MOTION_API_URL: "http://127.0.0.1:8765",
      MOTION_ALLOW_INSECURE_LOCAL: "true",
    }).origin,
    "http://127.0.0.1:8765",
  );
});

test("manifest rejects arbitrary assets, hashes, paths and memory budgets", async () => {
  const { validateManifest } = await import("../worker-protocol.mjs");
  const id = "b1337371-c1e4-4d02-8557-a73b24b0dc7f";
  const fixture = {
    render_id: id,
    lease: id,
    mode: "preview",
    spec_hash: "a".repeat(64),
    assets: [],
  };
  assert.doesNotThrow(() => validateManifest(fixture));
  const asset = {
    id,
    kind: "video",
    byte_size: 100,
    mime_type: "video/mp4",
    sha256: "a".repeat(64),
  };
  assert.doesNotThrow(() => validateManifest({ ...fixture, assets: [asset] }));
  for (const override of [
    { id: "../../etc/passwd" },
    { sha256: "not-sha" },
    { byte_size: 90 * 1024 * 1024 },
    { kind: "html" },
    { mime_type: "text/html" },
  ]) {
    assert.throws(() =>
      validateManifest({ ...fixture, assets: [{ ...asset, ...override }] }),
    );
  }
  assert.throws(() => validateManifest({ ...fixture, assets: [asset, asset] }));
});

test("worker authorization comparison fails closed", async () => {
  const { authorized } = await import("../worker-protocol.mjs");
  assert.equal(authorized("Bearer " + "x".repeat(40), "x".repeat(40)), true);
  assert.equal(authorized("Bearer " + "y".repeat(40), "x".repeat(40)), false);
  assert.equal(authorized("", ""), false);
  assert.equal(authorized("Bearer x", "x"), false);
});
