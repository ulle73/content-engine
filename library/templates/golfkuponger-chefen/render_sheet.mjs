// Karaktärsark för Chefen: node library/templates/golfkuponger-chefen/render_sheet.mjs [ut.jpg] [ut.mp4]
import { launch } from '../../../.claude/skills/animate/tools/pw.mjs';
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..', '..', '..');
const [still = path.join(ROOT, 'library/previews/golfkuponger.character.chefen.jpg'), video] = process.argv.slice(2);
const logo = 'data:image/png;base64,' + fs.readFileSync(path.join(ROOT, 'library/templates/golfkuponger-outro/assets/logo-final.png')).toString('base64');

const b = await launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
await p.goto(pathToFileURL(path.join(HERE, 'sheet.html')).href);
await p.evaluate(async (src) => { window.GK_LOGO = src; const i = new Image(); i.src = src; await i.decode(); await document.fonts.load('120px Anton'); await document.fonts.load('700 34px Inter'); await document.fonts.ready; }, logo);
const stage = await p.$('#stage');
await p.evaluate(() => draw(0.5)); await new Promise((r) => setTimeout(r, 150));
const png = path.join(HERE, '.sheet.png'); fs.writeFileSync(png, await stage.screenshot());
await new Promise((r) => spawn('ffmpeg', ['-v', 'error', '-y', '-i', png, '-vf', 'scale=540:-2', '-q:v', '3', still], { stdio: 'inherit' }).on('close', r));
fs.unlinkSync(png);
if (video) {
  const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', '30', '-i', '-', '-vf', 'scale=540:-2', '-c:v', 'libx264', '-crf', '26', '-pix_fmt', 'yuv420p', video], { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let i = 0; i < 90; i++) { await p.evaluate((t) => draw(t), i / 30); ff.stdin.write(await stage.screenshot()); }
  ff.stdin.end(); await new Promise((r) => ff.on('close', r));
}
await b.close();
console.log('klar', still, video || '');
