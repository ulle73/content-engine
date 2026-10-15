// Stilbilder: node work/gk-arsskifte/sf-render.mjs -> out/sf/<namn>.png + out/sf-sheet.png
import { launch } from '../../.claude/skills/animate/tools/pw.mjs';
import { execFileSync } from 'node:child_process';
import path from 'node:path'; import fs from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
const HERE = path.dirname(fileURLToPath(import.meta.url)), OUT = path.join(HERE, 'out', 'sf');
fs.mkdirSync(OUT, { recursive: true });
const b = await launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
await p.goto(pathToFileURL(path.join(HERE, 'src', 'styleframes.html')).href);
await p.evaluate(() => window.SF.ready);
const names = await p.evaluate(() => SF.names), stage = await p.$('#stage'), files = [];
for (const n of names) { await p.evaluate((nn) => SF.render(nn, 1.0), n); const f = path.join(OUT, `${n}.png`); fs.writeFileSync(f, await stage.screenshot()); files.push(f); }
await b.close();
const inputs = files.flatMap((f) => ['-i', f]);
const flt = files.map((_, i) => `[${i}:v]scale=360:-1,drawtext=text='${names[i]}':x=10:y=10:fontsize=24:fontcolor=white:box=1:boxcolor=black@0.6[v${i}]`).join(';');
const lay = files.map((_, i) => `${(i % 4) * 360}_${Math.floor(i / 4) * 640}`).join('|');
execFileSync('ffmpeg', ['-v', 'error', '-y', ...inputs, '-filter_complex', `${flt};${files.map((_, i) => `[v${i}]`).join('')}xstack=inputs=${files.length}:layout=${lay}:fill=black`, path.join(HERE, 'out', 'sf-sheet.png')]);
console.log('klar', names.join(', '));
