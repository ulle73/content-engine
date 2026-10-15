// Renderar scenen bildruta för bildruta i Chrome och kodar med ffmpeg.
//   node work/gk-arsskifte/render.mjs stills 0.5,3,6.4,9.5,12.2,12.36,13.0,15.6,17.7 out/sheet.png
//   node work/gk-arsskifte/render.mjs video out/film-9x16.mp4
import { launch } from '../../.claude/skills/animate/tools/pw.mjs';
import { spawn, execFileSync } from 'node:child_process';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const [mode, arg1, arg2] = process.argv.slice(2);

// Läsregeln (skills/video-regler): max(5/6, tecken/12) + 0,9 s. Stoppar renderingen.
function checkReading(texts) {
  const bad = [];
  for (const t of texts) {
    const chars = t.lines.join(' ').replace(/[{}]/g, '').length;
    const need = Math.round((Math.max(5 / 6, chars / 12) + 0.9) * 100) / 100, have = t.win[1] - t.win[0];
    console.log(`läsregel ${t.id}: ${chars} tecken, behöver ${need.toFixed(2)} s, har ${have.toFixed(2)} s ${have + 1e-6 >= need ? 'OK' : 'FÖR KORT'}`);
    if (have + 1e-6 < need) bad.push(t.id);
  }
  if (bad.length) { console.error('STOPP: läsregeln bryts för ' + bad.join(', ')); process.exit(2); }
}

const browser = await launch();
const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
await page.goto(pathToFileURL(path.join(HERE, 'src', process.env.PAGE || 'scene.html')).href);
await page.evaluate(() => window.SCENE.ready);
const meta = await page.evaluate(() => ({ duration: SCENE.duration, fps: SCENE.FPS, texts: SCENE.TEXTS }));
checkReading(meta.texts);
const stage = await page.$('#stage');
const shot = async (t) => { await page.evaluate((tt) => SCENE.renderAt(tt), t); return stage.screenshot({ type: 'png' }); };

if (mode === 'stills') {
  const times = arg1.split(',').map(Number), outDir = path.join(HERE, 'out', 'stills');
  fs.mkdirSync(outDir, { recursive: true });
  const files = [];
  for (const t of times) { const f = path.join(outDir, `t${t.toFixed(2)}.png`); fs.writeFileSync(f, await shot(t)); files.push(f); }
  if (arg2) {
    const cols = Math.min(files.length, 5), rows = Math.ceil(files.length / cols);
    const inputs = files.flatMap((f) => ['-i', f]);
    const scaled = files.map((_, i) => `[${i}:v]scale=360:-1,drawtext=text='${times[i].toFixed(2)}s':x=10:y=10:fontsize=26:fontcolor=white:box=1:boxcolor=black@0.5[v${i}]`).join(';');
    const layout = files.map((_, i) => `${(i % cols) * 360}_${Math.floor(i / cols) * 640}`).join('|');
    const pad = rows * cols - files.length;
    execFileSync('ffmpeg', ['-v', 'error', '-y', ...inputs, '-filter_complex',
      `${scaled};${files.map((_, i) => `[v${i}]`).join('')}xstack=inputs=${files.length}:layout=${layout}:fill=black`, path.resolve(arg2)]);
    console.log('kontaktkarta', arg2, pad ? `(${pad} tomma rutor)` : '');
  }
} else if (mode === 'video') {
  const out = path.resolve(arg1), n = Math.round(meta.duration * meta.fps);
  fs.mkdirSync(path.dirname(out), { recursive: true });
  const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(meta.fps), '-i', '-',
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let i = 0; i < n; i++) {
    const buf = await shot(i / meta.fps);
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
    if (i % 60 === 0) console.log(`bildruta ${i}/${n}`);
  }
  ff.stdin.end();
  await new Promise((r) => ff.on('close', r));
  console.log('klar', out);
}
await browser.close();
