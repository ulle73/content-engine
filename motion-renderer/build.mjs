import { bundle } from "@remotion/bundler";
import { buildAudio } from "./audio-assets.mjs";
import path from "node:path";
import { fileURLToPath } from "node:url";
const root = fileURLToPath(new URL(".", import.meta.url));
buildAudio(path.join(root, "public/audio"));
await bundle({
  entryPoint: path.join(root, "src/Root.tsx"),
  outDir: path.join(root, "build"),
  publicDir: path.join(root, "public"),
  onProgress: () => {},
});
console.log("Remotion production bundle built.");
