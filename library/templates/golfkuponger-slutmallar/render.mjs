// Slutmallar för Golfkuponger (Jonas 2026-11-16): den rörliga svingloggan + två fria textrader + portal(er).
//   node render.mjs --mall alla --rad1 "Friskvårdsbidrag kvar?" --rad2 "Det brinner inne 31/12" --ut work/slutmallar [--format 9x16,4x5]
//   node render.mjs --json jobb.json      ({ "mall", "rad1", "rad2", "effekt", "stil": {...}, "ut", "format": ["9x16","4x5"] })
// mall: alla | epassi | benify | sp | edenred.  *ord* i rad 2 blir guld.
// effekt (--eff): small | studs | tona | glid | skriv | avtack.  stil (--stil "logga=120,luft_logga=40"): se STIL i slutmall.html.
// Ut: <ut>/slutmall-<mall>-<9x16|4x5>.mp4 + kontakt-<format>.jpg, och en JSON-rad på stdout med filer, längd och textmått.
import fs from 'node:fs'; import path from 'node:path'; import { execFileSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
let ROT = HERE; while (!fs.existsSync(path.join(ROT, 'manage.py')) && path.dirname(ROT) !== ROT) ROT = path.dirname(ROT);
const { launch } = await import(pathToFileURL(path.join(ROT, '.claude/skills/animate/tools/pw.mjs')).href);
const arg = n => { const i = process.argv.indexOf(n); return i > 0 ? process.argv[i + 1] : null; };
const jobb = arg('--json') ? JSON.parse(fs.readFileSync(arg('--json'), 'utf8')) : {};
const MALL = jobb.mall || arg('--mall') || 'alla';
const RAD1 = jobb.rad1 ?? arg('--rad1') ?? 'Friskvårdsbidrag kvar?', RAD2 = jobb.rad2 ?? arg('--rad2') ?? 'Det brinner inne 31/12';
const UT = path.resolve(jobb.ut || arg('--ut') || path.join(ROT, 'work', 'slutmallar'));
const FORMAT = [].concat(jobb.format || (arg('--format') || '9x16,4x5').split(','));
const EFFEKT = jobb.effekt || arg('--eff') || 'small';
// stil: { logga: 120, luft_logga: 40, ... } – se STIL i slutmall.html. Från CLI: --stil "logga=120,luft_logga=40"
const STIL = jobb.stil || Object.fromEntries((arg('--stil') || '').split(',').filter(Boolean).map(p => p.split('=')));
if (!['small', 'studs', 'tona', 'glid', 'skriv', 'avtack'].includes(EFFEKT)) throw new Error(`okänd effekt: ${EFFEKT}`);
const SVING = process.env.SLUTMALL_SVING || path.join(ROT, 'edit-renderer/outros/golfkuponger/spotlight-9x16.mp4');
const FPS = 30;
if (!['alla', 'epassi', 'benify', 'sp', 'edenred'].includes(MALL)) throw new Error(`okänd mall: ${MALL}`);
if (!RAD2.trim()) throw new Error('rad 2 får inte vara tom');
if (RAD1.length > 40 || RAD2.length > 48) throw new Error('för lång text: rad 1 högst 40 tecken, rad 2 högst 48');
fs.mkdirSync(UT, { recursive: true });
const ff = a => execFileSync('ffmpeg', ['-v', 'error', '-y', ...a]);

const b = await launch(), resultat = { mall: MALL, rad1: RAD1, rad2: RAD2, filer: [] };
try {
  for (const fmt of FORMAT) {
    const H = fmt === '4x5' ? 1350 : 1920;
    const p = await b.newPage({ viewport: { width: 1080, height: H } });
    const q = new URLSearchParams({ mall: MALL, r1: RAD1, r2: RAD2, h: String(H), eff: EFFEKT });
    for (const [k, v] of Object.entries(STIL)) if (/^[a-z_]+$/.test(k) && Number.isFinite(Number(v))) q.set('s_' + k, String(v));
    await p.goto(pathToFileURL(path.join(HERE, 'slutmall.html')).href + '?' + q);
    await p.waitForFunction(() => window.INFO, null, { timeout: 30000 });   // sidan mäter texten först när typsnitten laddats
    const info = await p.evaluate(() => window.INFO), LEN = info.langd;
    const rutor = path.join(UT, `rutor-${fmt}`); fs.rmSync(rutor, { recursive: true, force: true }); fs.mkdirSync(rutor);
    for (let i = 0; i < Math.round(LEN * FPS); i++) {
      await p.evaluate(t => window.frame(t), i / FPS);
      await p.screenshot({ path: path.join(rutor, `${String(i).padStart(4, '0')}.jpg`), type: 'jpeg', quality: 93 });
    }
    await p.close();
    // svingloggan: loggans ram i spotlight-9x16.mp4 är x 160–919, y 401–1234 (mitt x 539,5). Beskär bort tagline, skala,
    // tona kanterna mot svart och lägg på med "lighten" i RGB (i YUV blev loggan rosa och fick en mörk ruta).
    const s = info.logga.h / 833, ox = Math.round(540 - 539.5 * s), oy = Math.round(info.logga.top - 401 * s);
    const F = 'clip((1-max(abs(X/W*2-1),abs(Y/H*2-1)))/0.08,0,1)';
    const ut = path.join(UT, `slutmall-${MALL}-${fmt}.mp4`);
    ff(['-framerate', String(FPS), '-i', path.join(rutor, '%04d.jpg'), '-i', SVING, '-filter_complex',
      `[1:v]crop=1080:1290:0:0,scale=-2:${Math.round(1290 * s / 2) * 2},format=gbrp,` +
      `geq=r='r(X,Y)*${F}':g='g(X,Y)*${F}':b='b(X,Y)*${F}',tpad=stop_mode=clone:stop_duration=${LEN}[l];` +
      `[0:v]format=gbrp,split[t0][t1];[t0][l]overlay=${ox}:${oy}:format=gbrp:eof_action=repeat[ov];` +
      `[t1][ov]blend=all_mode=lighten,format=yuv420p,trim=duration=${LEN}[v];` +
      `[1:a]aformat=sample_rates=48000:channel_layouts=stereo,apad,atrim=0:${LEN},afade=t=out:st=${(LEN - 0.5).toFixed(2)}:d=0.5[a]`,
      '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', '-r', String(FPS),
      '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', ut]);
    fs.rmSync(rutor, { recursive: true, force: true });
    ff(['-i', ut, '-f', 'null', '-']);   // leveransfilen ska gå att avkoda
    const tider = [0.13, 0.33, 0.53, 0.7, 0.85].map(andelen => LEN * andelen).concat(LEN - 0.1);
    const kontakt = path.join(UT, `kontakt-${MALL}-${fmt}.jpg`);
    ff([...tider.flatMap(t => ['-ss', t.toFixed(2), '-i', ut]), '-filter_complex',
      tider.map((_, i) => `[${i}:v]scale=300:-2,trim=end_frame=1[k${i}]`).join(';') + ';' + tider.map((_, i) => `[k${i}]`).join('') + `hstack=inputs=${tider.length}`,
      '-frames:v', '1', kontakt]);
    resultat.filer.push({ format: fmt, fil: ut, kontakt, langd: LEN, ...info });
    console.error(`${fmt}: ${LEN} s, effekt ${info.effekt}, rubrik ${info.rubrik_px} px på ${info.rubrik_rader} rad(er), botten y ${info.botten}`);
    for (const v of info.varningar || []) console.error(`  varning: ${v}`);
  }
} finally { await b.close(); }
console.log(JSON.stringify(resultat));
