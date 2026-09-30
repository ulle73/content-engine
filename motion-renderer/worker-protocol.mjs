/** Authenticated protocol for one fixed Content Engine origin. No remote code or URLs in jobs. */
import { timingSafeEqual, createHash } from "node:crypto";
import { createWriteStream, openAsBlob, statSync } from "node:fs";
import { once } from "node:events";
import path from "node:path";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const HASH = /^[0-9a-f]{64}$/;
const MIMES = {
  image: ["image/png", "image/jpeg", "image/webp"],
  video: ["video/mp4"],
  audio: ["audio/wav", "audio/mpeg", "audio/mp4"],
};
export const MAX_ASSET_BYTES = 80 * 1024 * 1024;
export const MAX_TOTAL_BYTES = 256 * 1024 * 1024;

export function configuration(env = process.env) {
  const url = new URL(env.MOTION_API_URL || "invalid:");
  const local =
    env.MOTION_ALLOW_INSECURE_LOCAL === "true" &&
    ["127.0.0.1", "localhost", "[::1]"].includes(url.hostname);
  if (
    (url.protocol !== "https:" && !(local && url.protocol === "http:")) ||
    url.username ||
    url.password ||
    url.search ||
    url.hash ||
    !["", "/"].includes(url.pathname)
  ) {
    throw new Error(
      "MOTION_API_URL must be a fixed HTTPS origin without credentials, query or path.",
    );
  }
  if ((env.MOTION_WORKER_TOKEN || "").length < 32)
    throw new Error("MOTION_WORKER_TOKEN must contain at least 32 characters.");
  if (
    !["evaluation", "eligible-free", "company-license"].includes(
      env.MOTION_LICENSE_MODE,
    )
  )
    throw new Error("Confirm Remotion licensing before starting this worker.");
  const port = Number(env.PORT || 8787);
  if (!Number.isSafeInteger(port) || port < 1 || port > 65535)
    throw new Error("Invalid worker port");
  return {
    origin: url.origin,
    token: env.MOTION_WORKER_TOKEN,
    port,
    licenseMode: env.MOTION_LICENSE_MODE,
  };
}

export function authorized(header, token) {
  if (
    typeof header !== "string" ||
    typeof token !== "string" ||
    token.length < 32
  )
    return false;
  const actual = Buffer.from(header);
  const expected = Buffer.from("Bearer " + token);
  return actual.length === expected.length && timingSafeEqual(actual, expected);
}

export function validateManifest(job) {
  if (
    !job ||
    !UUID.test(job.render_id) ||
    !UUID.test(job.lease) ||
    !["preview", "final"].includes(job.mode) ||
    !HASH.test(job.spec_hash) ||
    !Array.isArray(job.assets)
  )
    throw new Error("Invalid job manifest");
  const ids = new Set();
  let total = 0;
  for (const asset of job.assets) {
    if (
      !UUID.test(asset.id) ||
      ids.has(asset.id) ||
      !HASH.test(asset.sha256) ||
      !MIMES[asset.kind]?.includes(asset.mime_type) ||
      !Number.isSafeInteger(asset.byte_size) ||
      asset.byte_size <= 0 ||
      asset.byte_size > MAX_ASSET_BYTES
    )
      throw new Error("Invalid asset manifest");
    ids.add(asset.id);
    total += asset.byte_size;
  }
  if (total > MAX_TOTAL_BYTES)
    throw new Error("Input media exceed the 256 MB job budget.");
  return job;
}

export class ProtocolError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

export function protocol(config) {
  const endpoint = (suffix) => config.origin + "/internal/motion/" + suffix;
  const headers = (lease) => ({
    Authorization: "Bearer " + config.token,
    ...(lease ? { "X-Motion-Lease": lease } : {}),
  });
  async function json(suffix, data = {}) {
    const response = await fetch(endpoint(suffix), {
      method: "POST",
      headers: { ...headers(), "Content-Type": "application/json" },
      body: JSON.stringify(data),
      redirect: "error",
      signal: AbortSignal.timeout(65000),
    });
    if (!response.ok)
      throw new ProtocolError(
        response.status,
        "Content Engine rejected worker request",
      );
    return response.json();
  }
  async function download(job, asset, directory, signal) {
    const response = await fetch(
      endpoint(`assets/${job.render_id}/${asset.id}/`),
      {
        headers: headers(job.lease),
        redirect: "error",
        signal: AbortSignal.any([signal, AbortSignal.timeout(120000)]),
      },
    );
    if (!response.ok)
      throw new ProtocolError(response.status, "Input media unavailable");
    const size = Number(response.headers.get("content-length"));
    if (size !== asset.byte_size) throw new Error("Input size changed");
    const filename = path.join(directory, asset.id);
    const output = createWriteStream(filename, { flags: "wx" });
    const digest = createHash("sha256");
    let bytes = 0;
    try {
      for await (const chunk of response.body) {
        bytes += chunk.length;
        if (bytes > asset.byte_size)
          throw new Error("Input exceeded byte budget");
        digest.update(chunk);
        if (!output.write(chunk)) await once(output, "drain");
      }
      output.end();
      await once(output, "finish");
    } catch (error) {
      output.destroy();
      throw error;
    }
    if (bytes !== asset.byte_size || digest.digest("hex") !== asset.sha256)
      throw new Error("Input content hash mismatch");
    return { ...asset, path: filename };
  }
  async function upload(job, filename, kind, metadata = {}) {
    if (!["keyframe", "output"].includes(kind))
      throw new Error("Invalid output kind");
    const maximum = kind === "keyframe" ? 8 * 1024 * 1024 : MAX_ASSET_BYTES;
    if (statSync(filename).size > maximum)
      throw new Error("Output exceeds upload budget");
    // openAsBlob streams the file; it does not keep an additional video-sized Buffer in RAM.
    const file = await openAsBlob(filename, {
      type: kind === "keyframe" ? "image/png" : "video/mp4",
    });
    for (let attempt = 0; attempt < 3; attempt++) {
      const form = new FormData();
      form.set("file", file, kind === "keyframe" ? "frame.png" : "video.mp4");
      for (const [key, value] of Object.entries(metadata))
        form.set(key, String(value));
      try {
        const response = await fetch(endpoint(`${kind}/${job.render_id}/`), {
          method: "POST",
          headers: headers(job.lease),
          body: form,
          redirect: "error",
          signal: AbortSignal.timeout(150000),
        });
        if (!response.ok)
          throw new ProtocolError(response.status, "Output upload rejected");
        return await response.json();
      } catch (error) {
        if (
          (error instanceof ProtocolError && error.status < 500) ||
          attempt === 2
        )
          throw error;
        await new Promise((resolve) =>
          setTimeout(resolve, 500 * (attempt + 1)),
        );
      }
    }
  }
  return { json, download, upload };
}
