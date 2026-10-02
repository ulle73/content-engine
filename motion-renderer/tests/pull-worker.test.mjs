import test from "node:test";
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { spawn } from "node:child_process";
import { once } from "node:events";

test(
  "pull session registers over outbound protocol and stops when idle",
  { timeout: 30000 },
  async () => {
    const calls = [];
    const api = createServer(async (req, res) => {
      let input = "";
      for await (const chunk of req) input += chunk;
      assert.equal(req.headers.authorization, "Bearer " + "t".repeat(40));
      calls.push({ path: req.url, data: JSON.parse(input) });
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(
        req.url.endsWith("/claim/") ? '{"job":null}' : '{"accepted":true}',
      );
    });
    await new Promise((resolve) => api.listen(0, "127.0.0.1", resolve));
    const probe = createServer();
    await new Promise((resolve) => probe.listen(0, "127.0.0.1", resolve));
    const workerPort = probe.address().port;
    await new Promise((resolve) => probe.close(resolve));
    const worker = spawn(process.execPath, ["worker.mjs"], {
      cwd: new URL("..", import.meta.url),
      env: {
        ...process.env,
        MOTION_API_URL: `http://127.0.0.1:${api.address().port}`,
        MOTION_ALLOW_INSECURE_LOCAL: "true",
        MOTION_WORKER_TOKEN: "t".repeat(40),
        MOTION_LICENSE_MODE: "eligible-free",
        MOTION_WORKER_MODE: "pull",
        MOTION_IDLE_SECONDS: "1",
        PORT: String(workerPort),
      },
      stdio: ["ignore", "pipe", "pipe"],
    });
    let output = "";
    worker.stdout.on("data", (chunk) => (output += chunk));
    worker.stderr.on("data", (chunk) => (output += chunk));
    try {
      const [code] = await once(worker, "exit");
      assert.equal(code, 0, output);
      assert.match(output, /motion_idle_shutdown/);
      assert.match(output, /"pull_only":true/);
      assert.equal(calls.length, 2);
      assert.equal(calls[0].path, "/internal/motion/claim/");
      assert.equal(calls[1].path, "/internal/motion/disconnect/");
      assert.equal(calls[0].data.worker_id, calls[1].data.worker_id);
      assert.match(calls[0].data.worker_id, /^[0-9a-f-]{36}$/);
    } finally {
      worker.kill();
      await new Promise((resolve) => api.close(resolve));
    }
  },
);
