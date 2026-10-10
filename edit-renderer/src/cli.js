#!/usr/bin/env node
// Local renderer: build and render a cut spec from local files, no server needed.
//   node src/cli.js smoke-media                                   generate the smoke-test clips (ffmpeg)
//   node src/cli.js render --spec fixtures/smoke-spec.json --inputs fixtures/smoke-inputs.json --out ../work/edit-smoke
//   ... add --dry-run to only build the composition and run the browser check (lint, layout, contrast, safe zones).
//   node src/cli.js contact-sheet <video.mp4> <sheet.png> [--every 1]           a frame grid for reviews
import { existsSync, mkdirSync, readFileSync } from 'node:fs';
import { dirname, isAbsolute, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { run } from './finish.js';
import { renderCut } from './render.js';

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(HERE, '..', '..');

function arg(name, fallback = null) {
  const i = process.argv.indexOf(`--${name}`);
  return i > -1 ? process.argv[i + 1] : fallback;
}
const flag = (name) => process.argv.includes(`--${name}`);

async function smokeMedia(outDir) {
  mkdirSync(outDir, { recursive: true });
  const lib = join(REPO, 'library', 'templates', 'golfkuponger-friskvard-v2', 'assets');
  const clips = [
    { name: 'clip-a.mp4', src: 'hero-skogsbana-g.jpg', zoom: "1+0.0016*on", x: "iw/2-(iw/zoom/2)+on*0.8", tone: null },
    { name: 'clip-b.mp4', src: 'klubb-halmstad-gk-g.jpg', zoom: "1.12-0.0007*on", x: "iw/2-(iw/zoom/2)-on*0.9", tone: 196 },
  ];
  for (const clip of clips) {
    const target = join(outDir, clip.name);
    if (existsSync(target)) continue;
    const vf = `scale=-2:2400,crop=1350:2400,zoompan=z='${clip.zoom}':x='${clip.x}':y='ih/2-(ih/zoom/2)':d=180:s=1080x1920:fps=30`;
    const audio = clip.tone ? ['-f', 'lavfi', '-i', `sine=frequency=${clip.tone}:sample_rate=48000`, '-c:a', 'aac', '-b:a', '128k', '-shortest'] : [];
    const { code, stderr } = await run('ffmpeg', ['-hide_banner', '-y', '-loop', '1', '-i', join(lib, clip.src), ...audio.slice(0, 4),
      '-vf', vf, '-t', '6', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', ...audio.slice(4), target]);
    if (code !== 0) throw new Error(stderr.slice(-500));
    console.log(`skapade ${target}`);
  }
}

/** One row of frames every `every` seconds (two rows for long cuts), 270 px wide each. */
async function contactSheet(video, out, every = 1) {
  const { stdout } = await run('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', video]);
  const n = Math.max(1, Math.floor(Number(stdout) / every));
  const cols = Math.min(n, 8);
  const rows = Math.ceil(n / cols);
  const { code, stderr } = await run('ffmpeg', ['-hide_banner', '-y', '-i', video, '-vf',
    `fps=1/${every},scale=270:-2,tile=${cols}x${rows}:padding=6:color=0x202020`, '-frames:v', '1', out]);
  if (code !== 0) throw new Error(stderr.slice(-400));
  console.log(`skapade ${out} (${n} bilder)`);
}

async function main() {
  const command = process.argv[2];
  if (command === 'smoke-media') {
    await smokeMedia(resolve(arg('out', join(REPO, 'work', 'edit-smoke', 'media'))));
    return;
  }
  if (command === 'contact-sheet') {
    await contactSheet(resolve(process.argv[3]), resolve(process.argv[4]), Number(arg('every', 1)));
    return;
  }
  if (command !== 'render') {
    console.log('Användning: cli.js smoke-media | render --spec <fil> --inputs <fil> --out <mapp> [--dry-run] [--no-lint] | contact-sheet <mp4> <png>');
    process.exit(2);
  }
  const specPath = resolve(arg('spec'));
  const inputsPath = resolve(arg('inputs'));
  const out = resolve(arg('out', join(REPO, 'work', 'edit-smoke')));
  const spec = JSON.parse(readFileSync(specPath, 'utf8'));
  const inputs = JSON.parse(readFileSync(inputsPath, 'utf8'));
  const base = dirname(inputsPath);
  const files = {};
  for (const [id, file] of Object.entries(inputs.files)) {
    files[id] = { ...file, path: isAbsolute(file.path) ? file.path : resolve(base, file.path) };
  }
  const started = Date.now();
  const result = await renderCut({
    spec, brand: inputs.brand || {}, files, workDir: out, logoId: inputs.logo_asset_id || null,
    dryRun: flag('dry-run'), skipLint: flag('no-lint'),
    onStage: (stage, p) => console.log(`[${stage}] ${Math.round(p * 100)}%`),
  });
  for (const w of result.warnings) console.log(`varning: ${w}`);
  if (result.master) {
    console.log(JSON.stringify({ master: result.master, preview: result.preview, ...result.meta,
      seconds: Math.round((Date.now() - started) / 1000) }, null, 2));
  } else {
    console.log(JSON.stringify({ project: result.project, total: result.total, beats: result.beats, sfx: result.sfx,
      typography: result.typography, safe: result.safe }, null, 2));
  }
}

main().catch((err) => {
  console.error(err.code ? `${err.code}: ${err.message}` : err);
  process.exit(1);
});
