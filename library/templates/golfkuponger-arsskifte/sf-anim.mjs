// Rörlig förhandsvisning av en stilbild: node work/gk-arsskifte/sf-anim.mjs <namn> <sekunder> -> out/sf/<namn>.mp4
import { launch } from '../../.claude/skills/animate/tools/pw.mjs';
import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const [name, secs = '3'] = process.argv.slice(2);
const b = await launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
await p.goto(pathToFileURL(path.join(HERE, 'src', 'styleframes.html')).href);
await p.evaluate(() => window.SF.ready);
const stage = await p.$('#stage'), n = Math.round(Number(secs) * 30);
const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', '30', '-i', '-', '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', path.join(HERE, 'out', 'sf', `${name}.mp4`)], { stdio: ['pipe', 'inherit', 'inherit'] });
for (let i = 0; i < n; i++) { await p.evaluate(([nn, t]) => SF.render(nn, t), [name, i / 30]); const buf = await stage.screenshot(); if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r)); }
ff.stdin.end(); await new Promise((r) => ff.on('close', r)); await b.close(); console.log('klar', name);
