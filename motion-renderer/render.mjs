/** Worker-local render entrypoint. Only trusted, downloaded files are served to Chromium. */
import {
  renderMedia,
  renderStill,
  selectComposition,
  openBrowser,
  makeCancelSignal,
} from "@remotion/renderer";
import { createServer } from "node:http";
import {
  createReadStream,
  existsSync,
  mkdirSync,
  readFileSync,
  statSync,
  writeFileSync,
} from "node:fs";
import path from "node:path";
import { validateSpec, validateBrand } from "./validate.mjs";

const ROOT = new URL(".", import.meta.url).pathname;
function positions(scenes) {
  let end = 0;
  return scenes.map((s) => {
    const start = end - s.transition_frames;
    end = start + s.duration_frames;
    return { id: s.id, start, end };
  });
}
export async function renderMotion({
  spec: input,
  brand,
  files = {},
  outputDir,
  mode = "preview",
  onProgress = () => {},
  signal,
  onlyStills = false,
}) {
  const spec = validateSpec(input);
  validateBrand(brand);
  if (!["preview", "final"].includes(mode))
    throw new Error("Invalid render mode");
  if (!existsSync(path.join(ROOT, "build/index.html")))
    throw new Error("Build the renderer before starting work");
  mkdirSync(outputDir, { recursive: true });
  const served = new Map();
  const assets = {};
  for (const [id, file] of Object.entries(files)) {
    if (
      !/^[0-9a-f-]{36}$/.test(id) ||
      !["image", "video", "audio"].includes(file.kind)
    )
      throw new Error("Invalid media mapping");
    if (!existsSync(file.path) || statSync(file.path).size > 80 * 1024 * 1024)
      throw new Error("Invalid local media file");
    served.set("/assets/" + id, file);
  }
  const server = createServer((req, res) => {
    if (!["GET", "HEAD"].includes(req.method)) {
      res.writeHead(405);
      res.end();
      return;
    }
    const file = served.get(req.url?.split("?")[0]);
    if (!file) {
      res.writeHead(404);
      res.end();
      return;
    }
    const size = statSync(file.path).size;
    const range = /^bytes=(\d+)-(\d*)$/.exec(req.headers.range || "");
    const start = range ? Number(range[1]) : 0;
    const end =
      range && range[2] ? Math.min(Number(range[2]), size - 1) : size - 1;
    if (start > end || start >= size) {
      res.writeHead(416, { "Content-Range": `bytes */${size}` });
      res.end();
      return;
    }
    res.writeHead(range ? 206 : 200, {
      "Content-Type": file.mime_type || "application/octet-stream",
      "Content-Length": end - start + 1,
      "Accept-Ranges": "bytes",
      ...(range ? { "Content-Range": `bytes ${start}-${end}/${size}` } : {}),
    });
    if (req.method === "HEAD") {
      res.end();
      return;
    }
    createReadStream(file.path, { start, end }).pipe(res);
  });
  await new Promise((resolve, reject) => {
    server.on("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  const port = server.address().port;
  for (const [id, file] of Object.entries(files))
    assets[id] = {
      src: `http://127.0.0.1:${port}/assets/${id}`,
      kind: file.kind,
      width: file.width ?? null,
      height: file.height ?? null,
      duration_seconds: file.duration_seconds ?? null,
    };
  const needed = new Set(
    [
      spec.end_card_asset_id,
      spec.audio.music_asset_id,
      brand.logo_asset_id,
      ...spec.scenes.flatMap((s) => [
        s.props.asset_id,
        s.props.secondary_asset_id,
      ]),
    ].filter(Boolean),
  );
  for (const id of needed) {
    if (!assets[id]) {
      server.close();
      throw new Error("Referenced asset not downloaded");
    }
  }
  const browserExecutable =
    process.env.REMOTION_BROWSER_EXECUTABLE || undefined;
  let browser;
  const { cancelSignal, cancel } = makeCancelSignal();
  const abort = () => cancel();
  signal?.addEventListener("abort", abort, { once: true });
  try {
    browser = await openBrowser("chrome", {
      browserExecutable,
      chromeMode: browserExecutable ? "chrome-for-testing" : "headless-shell",
      logLevel: "error",
    });
    const inputProps = { spec, brand, assets };
    const serveUrl = path.join(ROOT, "build");
    const composition = await selectComposition({
      serveUrl,
      id: "Motion",
      inputProps,
      puppeteerInstance: browser,
      logLevel: "error",
    });
    const scale = mode === "preview" ? 1 / 3 : 1;
    const shared = {
      serveUrl,
      inputProps,
      composition,
      puppeteerInstance: browser,
      logLevel: "error",
      scale,
      timeoutInMilliseconds: 45000,
    };
    const keyframes = [];
    const times = positions(spec.scenes);
    if (mode === "preview" || onlyStills) {
      for (const [i, time] of times.entries()) {
        if (signal?.aborted) throw new Error("Canceled");
        const frame = Math.min(
          time.end - 1,
          time.start +
            Math.max(
              spec.scenes[i].transition_frames + 1,
              Math.floor((time.end - time.start) * 0.7),
            ),
        );
        const filename = path.join(outputDir, `keyframe-${time.id}.png`);
        await renderStill({
          ...shared,
          frame,
          output: filename,
          imageFormat: "png",
        });
        keyframes.push({ scene_id: time.id, frame, path: filename });
      }
    }
    const video = path.join(outputDir, mode + ".mp4");
    if (!onlyStills)
      await renderMedia({
        ...shared,
        outputLocation: video,
        codec: "h264",
        audioCodec: "aac",
        enforceAudioTrack: true,
        pixelFormat: "yuv420p",
        crf: mode === "preview" ? 26 : 20,
        concurrency: 1,
        disallowParallelEncoding: true,
        offthreadVideoCacheSizeInBytes: 32 * 1024 * 1024,
        offthreadVideoThreads: 1,
        mediaCacheSizeInBytes: 32 * 1024 * 1024,
        x264Preset: "veryfast",
        cancelSignal,
        onProgress: ({ progress }) => onProgress(progress),
        metadata: {
          comment: "Content Engine MotionSpec v1",
          creation_time: "1970-01-01T00:00:00Z",
        },
      });
    const result = {
      video: onlyStills ? null : video,
      keyframes,
      width: Math.round(composition.width * scale),
      height: Math.round(composition.height * scale),
      fps: composition.fps,
      duration_frames: composition.durationInFrames,
    };
    writeFileSync(
      path.join(outputDir, "render-result.json"),
      JSON.stringify(result, null, 2),
    );
    return result;
  } finally {
    signal?.removeEventListener("abort", abort);
    if (browser) await browser.close({ silent: true });
    await new Promise((resolve) => server.close(resolve));
  }
}
if (process.argv[1] === new URL(import.meta.url).pathname) {
  const filename = process.argv[2];
  if (!filename) {
    console.error("Usage: node render.mjs trusted-job.json");
    process.exit(2);
  }
  const input = JSON.parse(readFileSync(filename, "utf8"));
  renderMotion({
    ...input,
    onProgress: (p) => {
      if (Math.round(p * 100) % 10 === 0) process.stdout.write(".");
    },
    onlyStills: process.argv.includes("--stills"),
  })
    .then((result) => console.log("\n" + JSON.stringify(result)))
    .catch((error) => {
      console.error(error);
      process.exitCode = 1;
    });
}
