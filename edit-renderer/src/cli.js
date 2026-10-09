#!/usr/bin/env node
// Local renderer: build and render a cut spec from local files, no server needed.
//   node src/cli.js smoke-media                                   generate the smoke-test clips (ffmpeg)
//   node src/cli.js render --spec fixtures/smoke-spec.json --inputs fixtures/smoke-inputs.json --out ../work/edit-smoke
//   ... add --dry-run to only build the composition and run `hyperframes lint`.
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

async function main() {
  const command = process.argv[2];
  if (command === 'smoke-media') {
    await smokeMedia(resolve(arg('out', join(REPO, 'work', 'edit-smoke', 'media'))));
    return;
  }
  if (command !== 'render') {
    console.log('Användning: cli.js smoke-media | render --spec <fil> --inputs <fil> --out <mapp> [--dry-run] [--no-lint]');
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
    console.log(`komposition: ${result.project} (${result.total} s)`);
  }
}

main().catch((err) => {
  console.error(err.code ? `${err.code}: ${err.message}` : err);
  process.exit(1);
});
