// Golfare i <stad>? med ny slutscen i stället för svingloggan (Jonas 2026-10-29, komplettering – originalen ligger kvar).
//   node rendera.mjs annonser/<stad>.json --musik musik/hallelujah-kor.mp3 --traff 2.48 --traff-b1 1.32   (först, ger out/<stad>/scen-v*)
//   node slutscen.mjs [stad ...] [--musik <fil>]   alla städer som har out/<stad>/scen-v1.mp4 om inga anges
// Slutscener (slutbild/slutscen.html, 4,2 s): portal / direkt med vår logga i fast form, och portal-svinglogga /
// direkt-svinglogga med den animerade svingloggan i mindre format på samma plats. Texten slår ner som i filmen.
// Musiken går över i slutscenen och klingar ut där (Jonas: "då kan ljudet gå över i denna slutbilden"): spåret spelar
// till sitt slut (saktas ned högst 6 %) och sista sekunden får en efterklang som tonar ut vid filmens slut.
// Ut: resultat/slutscener/<stad>/golfare-i-<stad>_<B1-slam|B2-snurr>_slut-<variant>.mp4, kontaktkartor i out/slutscener/.
import fs from 'node:fs'; import path from 'node:path'; import { execFileSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
let ROT = HERE; while (!fs.existsSync(path.join(ROT, 'manage.py')) && path.dirname(ROT) !== ROT) ROT = path.dirname(ROT);
const { launch } = await import(pathToFileURL(path.join(ROT, '.claude/skills/animate/tools/pw.mjs')).href);
const arg = n => { const i = process.argv.indexOf(n); return i > 0 ? process.argv[i + 1] : null; };
const FPS = 30, SLUTLANGD = 4.2, MUSIK_ARG = arg('--musik') && path.resolve(arg('--musik'));
// --format 4x5: feedversionen (1080×1350) av scenerna i out/<stad>-4x5/ (rendera.mjs --format 4x5); filnamn med _4x5
const FORMAT = arg('--format') || '9x16', H = FORMAT === '4x5' ? 1350 : 1920, SUFFIX = FORMAT === '4x5' ? '_4x5' : '';
const DY = H === 1920 ? 0 : Math.round(H / 2 - 778);   // samma förskjutning som i slutscen.html
const VARIANTER = ['portal', 'direkt', 'portal-svinglogga', 'direkt-svinglogga'];
// svingloggan: loggans ram i spotlight-9x16.mp4 är x 160–919, y 401–1234; läggs där den fasta loggan står i slutscenen
const SVING = { portal: { s: 305 / 833, x: 427, y: 306 }, direkt: { s: 435 / 833, x: 379, y: 353 } };
// träffpunkt och landning läses ur out/<stad>/scen-v<v>.json (skrivs av rendera.mjs); annars Halleluja-körens standard
const FILM = { 1: { namn: 'B1-slam', traff: 1.32, landning: 1.45 }, 2: { namn: 'B2-snurr', traff: 2.48, landning: 2.43 } };
const OUTS = path.join(HERE, 'out', 'slutscener'); fs.mkdirSync(OUTS, { recursive: true });
const ff = a => execFileSync('ffmpeg', ['-v', 'error', '-y', ...a]);
const tid = f => +execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f]).toString();

// ---- 1. slutscenerna (en gång, samma för alla städer)
const b = await launch(), p = await b.newPage({ viewport: { width: 1080, height: H } });
for (const v of VARIANTER) {
  const ut = path.join(OUTS, `slut-${v}${SUFFIX}.mp4`), rutor = path.join(OUTS, `rutor-${v}${SUFFIX}`);
  const [bas, sving] = v.split('-');
  const h = sving ? `${bas}-anim` : bas;   // ?v= tvingar fram en ny laddning – bara #-byte kör inte om sidans skript
  await p.goto(pathToFileURL(path.join(HERE, 'slutbild', 'slutscen.html')).href + `?v=${h}&h=${H}#${h}`);
  await p.evaluate(() => document.fonts.ready);
  fs.rmSync(rutor, { recursive: true, force: true }); fs.mkdirSync(rutor);
  for (let i = 0; i < Math.round(SLUTLANGD * FPS); i++) {
    await p.evaluate(t => window.frame(t), i / FPS);
    await p.screenshot({ path: path.join(rutor, `${String(i).padStart(4, '0')}.jpg`), type: 'jpeg', quality: 93 });
  }
  const text = path.join(OUTS, `text-${v}${SUFFIX}.mp4`);
  ff(['-framerate', String(FPS), '-i', path.join(rutor, '%04d.jpg'), '-c:v', 'libx264', '-crf', '14', '-pix_fmt', 'yuv420p', text]);
  if (!sving) fs.renameSync(text, ut);
  else {
    // svingloggan: beskär bort "Mer golf. Fler upplevelser.", skala ned, tona kanterna mot svart och lägg på med "lighten"
    // så att den mörka bakgrunden försvinner. Sista bilden står kvar när svingloggans 3,1 s är slut.
    const { s, x, y } = SVING[bas], ox = Math.round(x - 160 * s), oy = Math.round(y - 401 * s) + DY;
    const F = "clip((1-max(abs(X/W*2-1),abs(Y/H*2-1)))/0.08,0,1)";
    ff(['-i', text, '-i', path.join(HERE, 'assets', 'spotlight-9x16.mp4'), '-filter_complex',
      `[1:v]crop=1080:1290:0:0,scale=-2:${Math.round(1290 * s / 2) * 2},format=gbrp,` +
      `geq=r='r(X,Y)*${F}':g='g(X,Y)*${F}':b='b(X,Y)*${F}',tpad=stop_mode=clone:stop_duration=${SLUTLANGD}[l];` +
      // allt i RGB – "lighten" på YUV gav rosa logga och en mörk ruta
      `[0:v]format=gbrp,split[t0][t1];[t0][l]overlay=${ox}:${oy}:format=gbrp:eof_action=repeat[ov];` +
      `[t1][ov]blend=all_mode=lighten,format=yuv420p,trim=duration=${SLUTLANGD}[v];` +
      `[1:a]aformat=sample_rates=48000:channel_layouts=stereo,apad,atrim=0:${SLUTLANGD}[a]`,
      '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-crf', '14', '-pix_fmt', 'yuv420p', '-c:a', 'pcm_s16le', ut.replace('.mp4', '.mov')]);
  }
  fs.rmSync(rutor, { recursive: true, force: true }); fs.rmSync(text, { force: true });
  console.log(`slutscen klar: ${v}`);
}
await b.close();

// ---- 2. scen + slutscen + musik per stad och film
const ARGS = process.argv.slice(2).filter((a, i, l) => !a.startsWith('--') && !['--musik', '--format'].includes(l[i - 1]));
const stader = ARGS.length ? ARGS
  : fs.readdirSync(path.join(HERE, 'out')).filter(d => !d.endsWith('-4x5') && fs.existsSync(path.join(HERE, 'out', d + (SUFFIX ? '-4x5' : ''), 'scen-v1.mp4')));
for (const kod of stader) for (const v of [1, 2]) for (const sv of VARIANTER) {
  const scen = path.join(HERE, 'out', kod + (SUFFIX ? '-4x5' : ''), `scen-v${v}.mp4`), LANGD = tid(scen), TOT = LANGD + SLUTLANGD;
  const info = fs.existsSync(scen.replace('.mp4', '.json')) ? JSON.parse(fs.readFileSync(scen.replace('.mp4', '.json'), 'utf8')) : {};
  const MUSIK = MUSIK_ARG || info.musik || path.join(HERE, 'musik', 'hallelujah-kor.mp3'), TL = tid(MUSIK);
  const sving = sv.includes('svinglogga'), slut = path.join(OUTS, `slut-${sv}${SUFFIX}.${sving ? 'mov' : 'mp4'}`);
  const { namn } = FILM[v], traff = info.traff ?? FILM[v].traff, landning = info.landning ?? FILM[v].landning;
  const tempo = Math.max(0.94, Math.min(1, (TL - traff) / (TOT - 2.0 - landning)));
  const start = Math.max(0, traff - tempo * landning), fordroj = Math.max(0, landning - traff / tempo);
  const slutMusik = fordroj + (TL - start) / tempo, ms = x => Math.round(x * 1000);
  const at = tempo < 1 ? `atempo=${tempo.toFixed(4)},` : '';
  const filter =
    `[0:v][1:v]concat=n=2:v=1:a=0[v];` +
    `[2:a]aformat=sample_rates=48000:channel_layouts=stereo,${at}afade=t=in:d=0.03,adelay=${ms(fordroj)}:all=1,apad[m];` +
    // efterklang: spårets sista sekund ekar ut (torra delen tas bort) och tonar ut till filmens slut
    `[3:a]aformat=sample_rates=48000:channel_layouts=stereo,${at}aecho=0.8:0.8:300|600|900|1200|1500|1800|2100|2400|2700|3000:0.5|0.42|0.35|0.28|0.22|0.17|0.13|0.1|0.07|0.05,` +
    `lowpass=f=6000,atrim=start=${(1 / tempo).toFixed(3)},asetpts=PTS-STARTPTS,afade=t=out:st=0:d=${Math.max(0.5, TOT - slutMusik).toFixed(3)},adelay=${ms(slutMusik)}:all=1,apad[e];` +
    (sving ? `[1:a]aformat=sample_rates=48000:channel_layouts=stereo,adelay=${ms(LANGD)}:all=1,apad[o];` : '') +
    `[m][e]${sving ? '[o]' : ''}amix=inputs=${sving ? 3 : 2}:normalize=0,atrim=0:${TOT.toFixed(3)},afade=t=out:st=${(TOT - 0.4).toFixed(3)}:d=0.4,loudnorm=I=-14:TP=-1.5[a]`;
  const dir = path.join(HERE, 'resultat', 'slutscener', kod); fs.mkdirSync(dir, { recursive: true });
  const ut = path.join(dir, `golfare-i-${kod}_${namn}_slut-${sv}${SUFFIX}.mp4`);
  ff(['-i', scen, '-i', slut, '-ss', start.toFixed(3), '-i', MUSIK, '-ss', (TL - 1.0).toFixed(3), '-i', MUSIK, '-filter_complex', filter,
    '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart', ut]);
  ff(['-i', ut, '-f', 'null', '-']);   // leveransfilen ska gå att avkoda
  const tider = [LANGD - 0.2, LANGD + 0.4, LANGD + 0.9, LANGD + 1.5, LANGD + 2.2, TOT - 0.1];
  ff([...tider.flatMap(t => ['-ss', t.toFixed(2), '-i', ut]), '-filter_complex',
    tider.map((_, i) => `[${i}:v]scale=300:-2,trim=end_frame=1[k${i}]`).join(';') + ';' + tider.map((_, i) => `[k${i}]`).join('') + `hstack=inputs=${tider.length}`,
    '-frames:v', '1', path.join(OUTS, `kontakt-${kod}-${namn}-${sv}${SUFFIX}.jpg`)]);
  console.log(`${kod} ${namn} ${sv}: ${TOT.toFixed(2)} s, musik ${tempo < 1 ? `tempo ${(tempo * 100).toFixed(1)} %, ` : ''}slutar ${slutMusik.toFixed(2)} s + efterklang`);
}
