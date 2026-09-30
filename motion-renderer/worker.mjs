/** One independently deployed worker. Django requests only enqueue/inspect jobs. */
import { createServer } from "node:http";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import {
  configuration,
  authorized,
  validateManifest,
  protocol,
  ProtocolError,
} from "./worker-protocol.mjs";
import { renderMotion } from "./render.mjs";

const config = configuration();
const api = protocol(config);
let active = false,
  stopping = false,
  controller = null,
  completed = 0,
  failed = 0;

async function runJob(raw) {
  const job = validateManifest(raw);
  const directory = await mkdtemp(path.join(tmpdir(), "ce-motion-"));
  controller = new AbortController();
  let progress = 0,
    lastHeartbeat = Date.now(),
    heartbeating = false,
    phase = "input";
  const deadline = setTimeout(
    () => controller?.abort("worker_timeout"),
    20 * 60 * 1000,
  );
  const heartbeat = setInterval(async () => {
    if (heartbeating) return;
    heartbeating = true;
    try {
      await api.json("heartbeat/", {
        render_id: job.render_id,
        lease: job.lease,
        progress,
      });
      lastHeartbeat = Date.now();
    } catch (error) {
      if (
        (error instanceof ProtocolError && [401, 409].includes(error.status)) ||
        Date.now() - lastHeartbeat > 120000
      )
        controller?.abort("lease_lost");
    } finally {
      heartbeating = false;
    }
  }, 10000);
  try {
    const files = {};
    for (const asset of job.assets)
      files[asset.id] = await api.download(
        job,
        asset,
        directory,
        controller.signal,
      );
    phase = "render";
    const result = await renderMotion({
      spec: job.spec,
      brand: job.brand,
      files,
      mode: job.mode,
      outputDir: directory,
      signal: controller.signal,
      onProgress: (value) => {
        progress = Math.max(progress, Math.min(0.95, value * 0.95));
      },
    });
    phase = "output";
    progress = 0.97;
    for (const frame of result.keyframes)
      await api.upload(job, frame.path, "keyframe", {
        scene_id: frame.scene_id,
        frame: frame.frame,
      });
    await api.upload(job, result.video, "output");
    completed++;
    console.log(
      JSON.stringify({
        event: "motion_completed",
        render_id: job.render_id,
        mode: job.mode,
      }),
    );
  } catch (error) {
    failed++;
    const code =
      controller.signal.reason === "worker_timeout"
        ? "worker_timeout"
        : phase === "input"
          ? "asset_missing"
          : phase === "output"
            ? "invalid_output"
            : "render_failed";
    console.error(
      JSON.stringify({
        event: "motion_failed",
        render_id: job.render_id,
        code,
        error_type: error?.constructor?.name,
      }),
    );
    try {
      await api.json("failed/", {
        render_id: job.render_id,
        lease: job.lease,
        code,
        retryable:
          !controller.signal.aborted &&
          (!(error instanceof ProtocolError) || error.status >= 500),
      });
    } catch {
      /* A fenced/canceled lease must not be resurrected. */
    }
  } finally {
    clearInterval(heartbeat);
    clearTimeout(deadline);
    controller = null;
    await rm(directory, { recursive: true, force: true });
  }
}

async function drain() {
  if (active || stopping) return;
  active = true;
  try {
    while (!stopping) {
      const response = await api.json("claim/");
      if (!response.job) break;
      await runJob(response.job);
    }
  } catch (error) {
    console.error(
      JSON.stringify({
        event: "motion_connection_deferred",
        error_type: error?.constructor?.name,
      }),
    );
  } finally {
    active = false;
  }
}

const server = createServer((req, res) => {
  if (req.method === "GET" && req.url === "/healthz") {
    res.writeHead(200, {
      "Content-Type": "application/json",
      "Cache-Control": "no-store",
    });
    res.end(
      JSON.stringify({
        status: "ok",
        renderer: "remotion",
        active,
        completed,
        failed,
      }),
    );
    return;
  }
  if (req.method === "POST" && req.url === "/wake") {
    if (!authorized(req.headers.authorization, config.token)) {
      res.writeHead(401);
      res.end();
      return;
    }
    if (Number(req.headers["content-length"] || 0) > 1024) {
      res.writeHead(413);
      res.end();
      return;
    }
    req.resume();
    res.writeHead(202, { "Content-Type": "application/json" });
    res.end('{"accepted":true}');
    void drain();
    return;
  }
  res.writeHead(404);
  res.end();
});
server.requestTimeout = 15000;
server.headersTimeout = 10000;
server.listen(config.port, "0.0.0.0", () => {
  console.log(
    JSON.stringify({ event: "motion_worker_ready", port: config.port }),
  );
  void drain();
});
const polling = setInterval(() => void drain(), 30000);
async function stop() {
  if (stopping) return;
  stopping = true;
  clearInterval(polling);
  controller?.abort("shutdown");
  server.close();
  const end = Date.now() + 10000;
  while (active && Date.now() < end)
    await new Promise((resolve) => setTimeout(resolve, 100));
  process.exit(0);
}
process.on("SIGTERM", () => void stop());
process.on("SIGINT", () => void stop());
