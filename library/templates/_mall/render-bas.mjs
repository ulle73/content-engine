// Gemensamt renderingsskelett för dashboardmallar (mall/v1). Varje mall har ett litet render.mjs:
//
//   import { cli } from '../_mall/render-bas.mjs';
//   await cli(import.meta.url);
//
//   node library/templates/<mall>/render.mjs --lokal [--format 4x5,9x16] [--satt rubrik="Hej"] [--json jobb.json] [--ut dir]
//
// Skelettet startar en liten lokal webbserver (sidan importerar moduler, och Chrome tillåter inte det från file://),
// öppnar sidan i Chrome via .claude/skills/animate/tools/pw.mjs, sätter window.PARAMS, väntar på window.KLAR, anropar
// window.frame(t) och skriver JPG/PNG eller skickar bildrutorna till ffmpeg. Ut: en JSON-rad på stdout med filerna.
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const ROT = path.resolve(HERE, '..', '..', '..');

// Uppmätt 2026-11-19 på Windows med Chrome 157: testmallen blev KLAR efter 0,11–0,17 s och slutmallen (window.INFO)
// efter 0,06–0,09 s. CI-jobbet skriver ut tiden för varje mall. Gränsen ger plats för en kall GitHub-runner och en
// bakgrundsbild på några MB från R2, men stoppar en sida som aldrig blir klar.
export const KLAR_GRANS_MS = 20000;

// Bara dessa delar av repot serveras, och bara till 127.0.0.1.
const TILLATET = ['library/', 'edit-renderer/outros/'];
// _mall/safezones.js finns inte som fil: den är edit-renderer/src/safezones.js (samma i Djangos förhandsvisning).
const VIRTUELLA = { 'library/templates/_mall/safezones.js': 'edit-renderer/src/safezones.js' };
const TYPER = {
  '.html': 'text/html; charset=utf-8', '.mjs': 'text/javascript', '.js': 'text/javascript', '.json': 'application/json',
  '.css': 'text/css', '.woff2': 'font/woff2', '.woff': 'font/woff', '.ttf': 'font/ttf', '.otf': 'font/otf',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.svg': 'image/svg+xml',
  '.mp4': 'video/mp4', '.webm': 'video/webm',
};

/**
 * Lokal statisk server för repot. extra = { '/library/templates/_mall/<namn>/': '<mapp>' } låter kontrollen visa en
 * kopia av en mall (t.ex. en trasig variant i självtestet) på samma djup som de riktiga mallarna.
 */
export async function startaServer({ extra = {} } = {}) {
  const server = http.createServer((req, res) => {
    try {
      if (req.method !== 'GET' && req.method !== 'HEAD') { res.writeHead(405).end(); return; }
      const url = decodeURIComponent(new URL(req.url, 'http://x').pathname);
      let fil = null;
      for (const [prefix, mapp] of Object.entries(extra)) {
        if (url.startsWith(prefix)) { fil = path.join(mapp, url.slice(prefix.length)); if (!path.resolve(fil).startsWith(path.resolve(mapp))) fil = null; break; }
      }
      if (!fil) {
        let rel = url.replace(/^\/+/, '');
        rel = VIRTUELLA[rel] || rel;
        if (!VIRTUELLA[url.replace(/^\/+/, '')] && !TILLATET.some(p => rel.startsWith(p)) || rel.includes('..')) { res.writeHead(404).end(); return; }
        fil = path.join(ROT, rel);
      }
      if (!fil || !fs.existsSync(fil) || !fs.statSync(fil).isFile()) { res.writeHead(404).end(); return; }
      res.writeHead(200, { 'content-type': TYPER[path.extname(fil).toLowerCase()] || 'application/octet-stream', 'cache-control': 'no-store' });
      if (req.method === 'HEAD') res.end(); else fs.createReadStream(fil).pipe(res);
    } catch { res.writeHead(500).end(); }
  });
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  const bas = `http://127.0.0.1:${server.address().port}`;
  return { bas, stang: () => new Promise(r => server.close(r)) };
}

let pw;
async function playwrightLaunch() {
  pw ||= await import(pathToFileURL(path.join(ROT, '.claude/skills/animate/tools/pw.mjs')).href);
  // Samma textrendering på alla datorer så långt det går (referensbilderna jämförs pixel för pixel).
  return pw.launch({ args: ['--font-render-hinting=none', '--disable-lcd-text', '--force-color-profile=srgb', '--hide-scrollbars'] });
}
export { playwrightLaunch as startaWebblasare };

export function lasMall(mallDir) {
  const mall = JSON.parse(fs.readFileSync(path.join(mallDir, 'mall.json'), 'utf8'));
  if (mall.schema !== 'mall/v1') throw new Error(`${mallDir}: mall.json har inte schema mall/v1`);
  return mall;
}

/** Sidans adress på servern: /library/templates/<mall>/<sida>. */
export function sidUrl(server, mallDir, mall, urlMapp) {
  const rel = urlMapp || '/' + path.relative(ROT, mallDir).split(path.sep).join('/') + '/';
  return server.bas + rel + mall.sida;
}

const STORLEK = { '9x16': [1080, 1920], '4x5': [1080, 1350], '1x1': [1080, 1080], '16x9': [1920, 1080] };

/**
 * Öppnar mallsidan för ett format och väntar på KLAR. Returnerar { page, info, klarMs }.
 * varden = reglagens värden (saknade fylls i av sidan från mall.json).
 */
export async function oppnaSida(browser, server, mallDir, { format, varden = {}, visaZoner = false, grans = KLAR_GRANS_MS, urlMapp, mall } = {}) {
  mall ||= lasMall(mallDir);
  if (!mall.format.includes(format)) throw new Error(`${mall.id}: formatet ${format} finns inte (${mall.format.join(', ')})`);
  const [bredd, hojd] = STORLEK[format];
  const page = await browser.newPage({ viewport: { width: bredd, height: hojd }, deviceScaleFactor: 1 });
  const fel = [];
  page.on('pageerror', e => fel.push(e.message));
  const params = { ...varden, format, visa_zoner: !!visaZoner };
  await page.addInitScript(p => { window.PARAMS = p; }, params);
  const start = Date.now();
  await page.goto(sidUrl(server, mallDir, mall, urlMapp));
  try {
    await page.waitForFunction(() => window.KLAR === true || window.MALLFEL, null, { timeout: grans, polling: 50 });
  } catch {
    await page.close();
    throw new Error(`Mallen laddade inte: ${mall.id} (${format}) blev inte KLAR inom ${grans / 1000} s` + (fel.length ? ` – ${fel[0]}` : ''));
  }
  const mallfel = await page.evaluate(() => window.MALLFEL || null);
  if (mallfel) { await page.close(); throw new Error(`Mallen ${mall.id} (${format}) kunde inte starta: ${mallfel.split('\n')[0]}`); }
  const klarMs = Date.now() - start;
  const info = await page.evaluate(() => window.INFO);
  return { page, info, klarMs, fel, mall };
}

export async function ritaRuta(page, t) {
  await page.evaluate(async x => { await window.frame(x); }, t);
}

/** Stillbild: ritar t och skriver JPG eller PNG. */
export async function fotaStill(page, ut, { t = 0, filtyp = 'jpg' } = {}) {
  await ritaRuta(page, t);
  await page.screenshot({ path: ut, type: filtyp === 'png' ? 'png' : 'jpeg', ...(filtyp === 'png' ? {} : { quality: 93 }) });
  return ut;
}

/**
 * Video: varje bildruta som PNG direkt in i ffmpeg (inga mellanfiler). Bildrutorna är ingång 0.
 * ljud = valfri ljudfil. En mall som behöver mer (t.ex. lägga på en film) ger egna ingångar (inArgs, ingång 1 och framåt)
 * och egna utdataargument (utArgs, ersätter standardkodningen; filnamnet läggs till sist).
 */
export async function filmaVideo(page, info, ut, { fps = info.fps || 30, ljud = null, inArgs = [], utArgs = null } = {}) {
  const antal = Math.round((info.langd || 0) * fps);
  if (!antal) throw new Error(`${info.mall} (${info.format}): sidan angav ingen längd i window.INFO.langd`);
  const args = ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(fps), '-i', '-', ...inArgs];
  if (utArgs) args.push(...utArgs, ut);
  else {
    if (ljud) args.push('-i', ljud, '-map', '0:v', '-map', '1:a', '-c:a', 'aac', '-b:a', '192k', '-shortest');
    args.push('-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', '-r', String(fps), '-movflags', '+faststart', ut);
  }
  const ff = spawn('ffmpeg', args, { stdio: ['pipe', 'inherit', 'inherit'] });
  const klar = new Promise((res, rej) => { ff.on('error', rej); ff.on('close', k => (k === 0 ? res() : rej(new Error(`ffmpeg avslutade med ${k}`)))); });
  for (let i = 0; i < antal; i++) {
    await ritaRuta(page, i / fps);
    const png = await page.screenshot({ type: 'png' });
    if (!ff.stdin.write(png)) await new Promise(r => ff.stdin.once('drain', r));
  }
  ff.stdin.end();
  await klar;
  return ut;
}

/**
 * Renderar alla utdata × format för en mall. Returnerar [{ typ, format, variant, filtyp, fil, bredd, hojd, langd, varningar }].
 * format = begränsa till dessa format (valfritt). Ett fel i en fil stoppar hela jobbet med filnamnet i felet.
 */
// videoVal({ info, format }) ger filmaVideo-val för mallen (egna ffmpeg-ingångar); efterVideo({ fil, info, format }) körs efter varje film.
// bildmapp: en mapp med jobbets uppladdade bilder; reglage av typen bild anger ett filnamn i den (servas som /_jobb/<fil>).
export async function renderaMall(mallDir, { varden = {}, format: bara, ut, browser: egen, videoVal, efterVideo, bildmapp } = {}) {
  const mall = lasMall(mallDir);
  ut = path.resolve(ut || path.join(ROT, 'work', 'mallar', mall.id));
  fs.mkdirSync(ut, { recursive: true });
  const server = await startaServer(bildmapp ? { extra: { '/_jobb/': path.resolve(bildmapp) } } : {});
  for (const r of mall.reglage) {
    if (r.typ === 'bild' && typeof varden[r.nyckel] === 'string' && /^[\w.-]+$/.test(varden[r.nyckel])) varden = { ...varden, [r.nyckel]: '/_jobb/' + varden[r.nyckel] };
  }
  const browser = egen || await playwrightLaunch();
  const filer = [];
  try {
    for (const u of mall.utdata) {
      for (const format of u.format.filter(f => !bara || bara.includes(f))) {
        const namn = `${mall.id}${u.variant ? '-' + u.variant : ''}-${format}.${u.filtyp}`;
        const fil = path.join(ut, namn);
        const { page, info } = await oppnaSida(browser, server, mallDir, { format, varden, mall });
        try {
          if (u.typ === 'bild') await fotaStill(page, fil, { filtyp: u.filtyp });
          else {
            await filmaVideo(page, info, fil, videoVal ? await videoVal({ info, format }) : {});
            if (efterVideo) Object.assign(info, (await efterVideo({ fil, info, format })) || {});
          }
        } catch (e) {
          throw new Error(`${namn}: ${e.message}`);
        } finally { await page.close(); }
        filer.push({ ...info, typ: u.typ, format, variant: u.variant || null, filtyp: u.filtyp, fil, bredd: info.bredd, hojd: info.hojd, langd: info.langd, varningar: info.varningar || [] });
        for (const v of info.varningar || []) console.error(`  varning (${namn}): ${v}`);
      }
    }
  } finally {
    if (!egen) await browser.close();
    await server.stang();
  }
  return filer;
}

function argv(namn) { const i = process.argv.indexOf(namn); return i > 0 ? process.argv[i + 1] : null; }

/**
 * CLI för en malls render.mjs: node render.mjs --lokal [--format 4x5] [--satt k=v ...] [--json jobb.json] [--ut dir]
 * jobb.json: { "varden": {...}, "format": ["4x5"], "ut": "dir", "bildmapp": "dir" }. Valen:
 *   tolka(jobb, argv)  gör om en äldre jobbfil eller äldre flaggor till { varden, format, ut } (före de nya)
 *   videoVal, efterVideo  skickas till renderaMall
 *   svar(filer, jobb)  formar JSON-raden på stdout (standard: { mall, filer })
 */
export async function cli(metaUrl, { tolka, videoVal, efterVideo, svar } = {}) {
  const mallDir = path.dirname(fileURLToPath(metaUrl));
  const jobb = argv('--json') ? JSON.parse(fs.readFileSync(argv('--json'), 'utf8')) : {};
  const gammal = tolka ? (tolka(jobb, argv) || {}) : {};
  const varden = { ...(gammal.varden || {}), ...(jobb.varden || {}) };
  process.argv.forEach((a, i) => {
    if (a !== '--satt') return;
    const [k, ...rest] = String(process.argv[i + 1] || '').split('=');
    const x = rest.join('=');
    varden[k] = x === 'true' ? true : x === 'false' ? false : (x !== '' && Number.isFinite(Number(x)) ? Number(x) : x);
  });
  const format = gammal.format || jobb.format || (argv('--format') ? argv('--format').split(',') : null);
  const ut = gammal.ut || jobb.ut || argv('--ut');
  const bildmapp = jobb.bildmapp || argv('--bildmapp');
  const filer = await renderaMall(mallDir, { varden, format, ut, videoVal, efterVideo, bildmapp });
  console.log(JSON.stringify(svar ? svar(filer, jobb) : { mall: path.basename(mallDir), filer }));
  return filer;
}