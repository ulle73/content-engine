/** Worker-local render entrypoint. Only trusted, downloaded files are served to Chromium. */
import {
  renderMedia,
  renderStill,
  selectComposition,
  openBrowser,
  makeCancelSignal,
} from "@remotion/renderer";
import { createServer } from "node:http";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import {
  createReadStream,
  existsSync,
  mkdirSync,
  readFileSync,
  statSync,
  writeFileSync,
  rmSync,
} from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { validateSpec, validateBrand } from "./validate.mjs";

const ROOT = fileURLToPath(new URL(".", import.meta.url));
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
    const binariesDirectory = process.env.REMOTION_BINARIES_DIRECTORY || null;
    const composition = await selectComposition({
      serveUrl,
      id: "Motion",
      inputProps,
      puppeteerInstance: browser,
      logLevel: "error",
      binariesDirectory,
    });
    const scale = mode === "preview" ? 1 / 3 : 1;
    const shared = {
      serveUrl,
      inputProps,
      composition,
      puppeteerInstance: browser,
      logLevel: "error",
      scale,
      binariesDirectory,
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
    // Portable FFmpeg builds have native AAC but not Remotion's libfdk_aac.
    // Keep lossless audio in an intermediate file, then mux native AAC into MP4.
    const intermediate = binariesDirectory
      ? path.join(outputDir, mode + "-intermediate.mkv")
      : video;
    if (!onlyStills) {
      await renderMedia({
        ...shared,
        outputLocation: intermediate,
        codec: binariesDirectory ? "h264-mkv" : "h264",
        audioCodec: binariesDirectory ? "pcm-16" : "aac",
        enforceAudioTrack: true,
        binariesDirectory,
        pixelFormat: "yuv420p",
        colorSpace: "bt709",
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
      if (binariesDirectory) {
        try {
          await promisify(execFile)(
            path.join(
              binariesDirectory,
              process.platform === "win32" ? "ffmpeg.exe" : "ffmpeg",
            ),
            [
              "-v",
              "error",
              "-y",
              "-i",
              intermediate,
              "-map",
              "0:v:0",
              "-map",
              "0:a:0",
              "-c:v",
              "copy",
              "-c:a",
              "aac",
              "-b:a",
              "192k",
              "-map_metadata",
              "-1",
              "-metadata",
              "comment=Content Engine MotionSpec v1",
              "-movflags",
              "+faststart",
              video,
            ],
            { signal, timeout: 120000, maxBuffer: 1024 * 1024 },
          );
        } finally {
          rmSync(intermediate, { force: true });
        }
      }
    }
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
if (
  process.argv[1] &&
  path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)
) {
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
