// Golfare i <stad>? – renderar stillbild, slam och snurr för en annons, med QA.
//   node rendera.mjs annonser/<stad>.json [--utkast] [--musik <fil> --traff <s>] [--bara-still]
//   --traff: tiden i musikspåret som ska slå exakt när stadsnamnet landar (B1 1,45 s, B2 2,43 s in i filmen);
//   --traff-b1/--traff-b2 för en variant. Halleluja-kören: --traff 2.48 --traff-b1 1.32 (kören börjar från första tonen i båda).
//   Musiken fortsätter 0,45 s in i slutbilden och tonar ut där ("musik_in_i_slutbild" i annonsen ändrar det).
//   Musik ur ljudbanken: python library/sounds/sounds.py copy <id> musik/<namn>.wav (se README för träffpunkter).
// Ut: resultat/<kod>/<namn>_A-still.jpg, <namn>_B1-slam.mp4, <namn>_B2-snurr.mp4 (filnamn kan styras med "filnamn" i annonsen)
//     out/<kod>/kontaktkarta-B1-slam.jpg, kontaktkarta-B2-snurr.jpg, kontroll-safezone.png
// Varnar om läsregeln bryts (stoppar med "lasregel": "stopp"). Stoppar om något ligger utanför safe zones, eller slutlägena i slam och snurr skiljer sig från stillbilden.
import fs from 'node:fs'; import path from 'node:path'; import { execFileSync, spawnSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
// repots rot (mappen med manage.py) – mallen fungerar både i library/templates/ och som kopia i work/<namn>/
let ROT = HERE; while (!fs.existsSync(path.join(ROT, 'manage.py')) && path.dirname(ROT) !== ROT) ROT = path.dirname(ROT);
const { launch } = await import(pathToFileURL(path.join(ROT, '.claude/skills/animate/tools/pw.mjs')).href);
const arg = n => { const i = process.argv.indexOf(n); return i > 0 ? process.argv[i + 1] : null; };
const stopp = m => { console.log('STOPP:', m); process.exit(1); };
const KONFIG = process.argv[2]; if (!KONFIG || KONFIG.startsWith('--')) stopp('ange en annons, t.ex. node rendera.mjs annonser/stockholm.json');
const UTKAST = process.argv.includes('--utkast'), BARA_STILL = process.argv.includes('--bara-still');
const MUSIK = arg('--musik'), TRAFF_ALLA = +(arg('--traff') || 0), FPS = 30;
const K = JSON.parse(fs.readFileSync(KONFIG, 'utf8'));
const kod = K.stad.toLowerCase().replace(/[åä]/g, 'a').replace(/ö/g, 'o').replace(/[^a-z0-9]+/g, '-');
const namn = K.namn || `golfare-i-${kod}`;
const filnamn = variant => (K.filnamn || `${namn}_{variant}`).replace('{variant}', variant);   // t.ex. "T01_format_{variant}_sthlm"

// ---- antal klubbar i regionen ur sajtens klubblista (aktiva golfbanor, klubben själv oräknad, avrundat nedåt till 5)
const REGION = {
  Stockholm: 'Stockholmsområdet', Göteborg: 'Göteborgsområdet', Malmö: 'Skåne', Lund: 'Skåne', Helsingborg: 'Skåne',
  Kristianstad: 'Skåne', Uppsala: 'Uppsala & Mälardalen', Västerås: 'Uppsala & Mälardalen', Eskilstuna: 'Uppsala & Mälardalen',
  Örebro: 'Värmland, Örebro & Dalarna', Karlstad: 'Värmland, Örebro & Dalarna', Falun: 'Värmland, Örebro & Dalarna',
  Borlänge: 'Värmland, Örebro & Dalarna', Linköping: 'Östergötland', Norrköping: 'Östergötland', Jönköping: 'Småland & Öland',
  Växjö: 'Småland & Öland', Kalmar: 'Småland & Öland', Umeå: 'Norrland', Sundsvall: 'Norrland', Luleå: 'Norrland',
  Östersund: 'Norrland', Gävle: 'Norrland', Halmstad: 'Halland', Varberg: 'Halland', Borås: 'Skaraborg & Sjuhärad',
  Skövde: 'Skaraborg & Sjuhärad', Uddevalla: 'Bohuslän & Dalsland', Karlskrona: 'Blekinge',
};
const LISTA = 'klubbdata/klubbar-sajt-2026-10-21.json';
const klubbar = JSON.parse(fs.readFileSync(path.join(HERE, LISTA), 'utf8')).filter(x => x.active && x.anlaggningstyp === 'golfbana');
const region = K.region || REGION[K.stad] || stopp(`okänd region för ${K.stad} – sätt "region" i annonsen (en av: ${[...new Set(klubbar.map(x => x.region))].join(', ')})`);
const iRegionen = klubbar.filter(x => x.region === region);
if (!iRegionen.length) stopp(`inga klubbar i regionen "${region}"`);
if (!iRegionen.some(x => x.name.toLowerCase().includes(K.klubb.toLowerCase()))) console.log(`VARNING: ${K.klubb} finns inte bland golfbanorna i ${region} i ${LISTA}`);
const andra = iRegionen.length - 1;
const antal = K.antal || (andra >= 5 ? `${Math.floor(andra / 5) * 5}+` : String(andra));
console.log(`${K.stad}: ${region}, ${iRegionen.length} golfbanor i ${LISTA} → "${K.klubb} och ${antal} andra"`);

// ---- klubbrullen: andra klubbar i regionen med korta namn ("Bro Hof Slott GC" → "Bro Hof Slott"), jämnt spridda i listan
const kortnamn = n => {   // "Bro Hof Slott GC" → "Bro Hof Slott"; genitiv behåller GK/GC ("Djursholms GK", inte "Spela Djursholms")
  let k = n.replace(/\s+AB$/i, '').replace(/\s+(GK|GC)\s+/g, ' ');
  for (let i = 0; i < 3; i++) k = k.replace(/\s+(Golf\s*&\s*Sports\s*Club|Golf\s*&\s*Country\s*Club|Golf\s*&\s*CC|G\s*&\s*CC|G&CC|Golfklubb|Golf\s*Club|Golfbana|Golfbanor|Resort|GK|GC|Golf)$/i, '');
  k = k.trim(); const suff = (n.match(/\b(GK|GC)\b/) || [])[1];
  return /s$/.test(k) && suff ? `${k} ${suff}` : k;
};
const ovriga = [...new Set(iRegionen.filter(x => !x.name.toLowerCase().includes(K.klubb.toLowerCase())).map(x => kortnamn(x.name)))]
  .filter(n => n.length >= 3 && n.length <= 16 && !/[´`'’]/.test(n) && n.toLowerCase() !== K.klubb.toLowerCase());
// stora klubbar i regionen (klubbdata/stora-klubbar.json) är alltid med; vikt 1 hamnar sist, närmast den utvalda klubben.
// Är listan kort fylls det på med jämnt spridda andra klubbar ur klubblistan.
const STORA = (JSON.parse(fs.readFileSync(path.join(HERE, 'klubbdata', 'stora-klubbar.json'), 'utf8'))[region] || [])
  .map(q => iRegionen.find(x => x.name.toLowerCase().includes(q.toLowerCase()))).filter(Boolean)
  .map(x => kortnamn(x.name)).filter(n => n.toLowerCase() !== K.klubb.toLowerCase() && !K.klubb.toLowerCase().includes(n.toLowerCase()));
// rullen visar de N största (standard 5); den största hamnar sist, närmast den utvalda klubben. Fylls på om listan är kort.
const ANTAL = K.antal_rulle || 5, storst = STORA.slice(0, ANTAL);
const fyll = ovriga.filter(n => !storst.includes(n)), extra = Math.max(0, ANTAL - storst.length);
const klubbrulle = K.klubbrulle || [...Array.from({ length: Math.min(extra, fyll.length) }, (_, i) => fyll[Math.floor(i * fyll.length / extra)]), ...[...storst].reverse()];
console.log(`klubbrullen: ${klubbrulle.join(', ')} → ${K.klubb}`);

const STADER = ['Göteborg', 'Malmö', 'Uppsala', 'Västerås', 'Örebro', 'Lund', 'Umeå', 'Sundsvall', 'Stockholm'];
const ANNONS = {
  stad: K.stad,
  rad1: K.rad1 || 'GOLFARE I',
  underrad: (K.underrad || 'Spela {klubb} och {antal} andra klubbar i regionen – på friskvårdsbidraget.').replace('{antal}', antal),
  klubb: K.klubb,
  bana: K.bana || (iRegionen.find(x => x.name.toLowerCase().includes(K.klubb.toLowerCase())) || {}).name || K.klubb,
  klubbrulle,
  langd: K.langd,
  knapp: K.knapp || 'Hitta din bana →',
  rulle: K.rulle || STADER.filter(s => s !== K.stad).slice(0, 8),
  foto: `annonser/${kod}/foto-1080.jpg`,
};

// ---- bilden: skalas till 1920 px höjd (eller 1080 px bredd) och beskärs till 9:16 med fokus 0–1 (vänster–höger / topp–botten)
const BILD = [path.resolve(path.dirname(KONFIG), K.bild), path.resolve(ROT, K.bild)].find(p => fs.existsSync(p)) || '';   // relativt annonsen eller repots rot
if (!fs.existsSync(BILD)) stopp(`hittar inte bilden ${BILD}`);
fs.mkdirSync(path.join(HERE, 'annonser', kod), { recursive: true });
const [bw, bh] = execFileSync('ffprobe', ['-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', BILD]).toString().trim().split(',').map(Number);
const fokus = K.fokus ?? 0.5;
const skala = bw / bh > 1080 / 1920 ? `scale=-2:1920:flags=lanczos,crop=1080:1920:(iw-1080)*${fokus}:0` : `scale=1080:-2:flags=lanczos,crop=1080:1920:0:(ih-1920)*${fokus}`;
execFileSync('ffmpeg', ['-v', 'error', '-y', '-i', BILD, '-vf', skala, '-q:v', '2', path.join(HERE, ANNONS.foto)]);

// ---- rendera
const RES = path.join(HERE, 'resultat', kod), OUT = path.join(HERE, 'out', kod);
for (const d of [RES, OUT]) fs.mkdirSync(d, { recursive: true });
const VAR = { 1: 'B1-slam', 2: 'B2-snurr' };
const b = await launch({ args: ['--allow-file-access-from-files'] });
const sidor = {};
for (const v of [1, 2]) {
  const ctx = await b.newContext({ viewport: { width: 1080, height: 1920 } });
  await ctx.addInitScript(a => { window.ANNONS = a; }, ANNONS);
  const p = await ctx.newPage();
  p.on('pageerror', e => stopp(`v${v} sidfel: ${e.message}`));
  await p.goto(pathToFileURL(path.join(HERE, 'film.html')).href + `?v=${v}`);
  const m = await p.evaluate(() => window.klar);
  const { TEXT, LANGD, FORSTA_TEXT, LANDNING } = await p.evaluate(() => ({ TEXT: window.TEXT, LANGD: window.LANGD, FORSTA_TEXT: window.FORSTA_TEXT, LANDNING: window.LANDNING }));
  const n = TEXT.join('').length, krav = FORSTA_TEXT + Math.max(5 / 6, n / 12) + 0.9;
  // Beslut Jonas 2026-10-28: filmen slutar när allt har landat (~7,5 s), inte efter läsregelns ~10 s – varna, stoppa inte.
  // "lasregel": "stopp" i annonsen gör kontrollen hård igen.
  if (LANGD < krav && K.lasregel === 'stopp') stopp(`v${v} läsregeln: text till ${krav.toFixed(2)} s krävs, scenen är ${LANGD} s`);
  console.log(LANGD < krav ? `v${v} VARNING läsregeln: ${n} tecken kräver ${krav.toFixed(2)} s, scenen är ${LANGD} s (kortare enligt beslut)` : `v${v} läsregeln ok (${n} tecken, ${krav.toFixed(2)} s ≤ ${LANGD} s)`);
  for (const [id, r] of Object.entries(m)) {
    const centrerad = id !== 'plats';   // bannamnet är vänsterställt nere till vänster
    const yMax = id === 'plats' ? 1600 : 1250;   // bannamnet ligger medvetet lägre (beslut Jonas 2026-10-28)
    const ok = r.x0 >= 65 && r.x1 <= 929 && r.y0 >= 270 && r.y1 <= yMax && (!centrerad || Math.abs(r.x0 - (1080 - r.x1)) <= 2);
    console.log(`v${v} ${ok ? 'ok ' : 'FEL'} ${id.padEnd(7)} x ${r.x0}–${r.x1}  y ${r.y0}–${r.y1}`);
    if (!ok) stopp(`v${v} ${id} utanför safe zones eller inte centrerad`);
  }
  sidor[v] = { p, LANGD, LANDNING };
  fs.writeFileSync(path.join(OUT, `slut-v${v}.png`), await p.screenshot());
}
// stillbilden = slutläget; slam och snurr måste sluta exakt där
const err = spawnSync('ffmpeg', ['-hide_banner', '-i', path.join(OUT, 'slut-v1.png'), '-i', path.join(OUT, 'slut-v2.png'), '-lavfi', 'psnr', '-f', 'null', '-']).stderr.toString();
const lik = (/average:(\S+)/.exec(err) || [])[1];
console.log(`slutläge slam mot snurr: PSNR ${lik} dB`);
if (lik !== 'inf' && parseFloat(lik) < 45) stopp('slutlägena i slam och snurr skiljer sig – stillbilden blir inte samma som båda');
execFileSync('ffmpeg', ['-v', 'error', '-y', '-i', path.join(OUT, 'slut-v2.png'), '-q:v', '2', path.join(RES, `${filnamn('A-still')}.jpg`)]);
await sidor[2].p.evaluate(() => { const d = document.createElement('div');
  d.style.cssText = 'position:absolute;inset:0;pointer-events:none;box-shadow:inset 0 270px 0 rgba(255,0,0,.25),inset 0 -670px 0 rgba(255,0,0,.25);border-left:151px solid rgba(255,0,0,.25);border-right:151px solid rgba(255,0,0,.25);box-sizing:border-box';
  document.body.appendChild(d); });
await sidor[2].p.screenshot({ path: path.join(OUT, 'kontroll-safezone.png') });
await sidor[2].p.evaluate(() => document.body.lastElementChild.remove());
console.log(`stillbild klar: resultat/${kod}/${filnamn('A-still')}.jpg`);

if (!BARA_STILL) for (const v of [1, 2]) {
  const { p, LANGD, LANDNING } = sidor[v], rutor = path.join(OUT, `rutor-v${v}`);
  fs.rmSync(rutor, { recursive: true, force: true }); fs.mkdirSync(rutor, { recursive: true });
  for (let i = 0; i < Math.round(LANGD * FPS); i++) {
    await p.evaluate(t => window.frame(t), i / FPS);
    await p.screenshot({ path: path.join(rutor, `${String(i).padStart(4, '0')}.jpg`), type: 'jpeg', quality: 93 });
  }
  const scen = path.join(OUT, `scen-v${v}.mp4`), fil = `${filnamn(VAR[v])}${UTKAST ? '-utkast' : ''}.mp4`;
  // Musiken: träffpunkten läggs på landningen, och musiken fortsätter in i slutbilden och tonar ut till
  // LANGD + MUSIK_IN_I_SLUT (≈ 8 s) – en kort paus innan svingloggans eget ljud (~1,17 s in i slutbilden).
  // Räcker spåret inte dit saktas det ned lite (tonhöjden behålls, högst 12 %) så att träffen ändå hamnar rätt.
  const SLUT = LANGD + (K.musik_in_i_slutbild ?? 0.45);
  const TRAFF = +(arg(`--traff-b${v}`) ?? TRAFF_ALLA);   // --traff-b1/--traff-b2 gäller en variant
  let tempo = 1, start = 0, fordroj = 0;
  if (MUSIK) {
    const TL = +execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path.resolve(MUSIK)]).toString();
    tempo = Math.max(0.88, Math.min(1, (TL - TRAFF) / (SLUT - LANDNING)));
    start = Math.max(0, TRAFF - tempo * LANDNING); fordroj = Math.max(0, LANDNING - TRAFF / tempo);
    console.log(`${VAR[v]}: musiken från ${start.toFixed(2)} s i spåret${fordroj ? `, börjar ${fordroj.toFixed(2)} s in` : ''}${tempo < 1 ? `, tempo ${(tempo * 100).toFixed(1)} %` : ''}, träff på ${LANDNING} s, tonar ut till ${SLUT.toFixed(2)} s`);
  }
  execFileSync('ffmpeg', ['-v', 'error', '-y', '-framerate', String(FPS), '-i', path.join(rutor, '%04d.jpg'),
    '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', scen]);
  const musik = MUSIK ? `[2:a]aformat=sample_rates=48000:channel_layouts=stereo,${tempo < 1 ? `atempo=${tempo.toFixed(4)},` : ''}` +
    `afade=t=in:d=0.03,adelay=${Math.round(fordroj * 1000)}:all=1,apad,atrim=0:${SLUT.toFixed(3)},afade=t=out:st=${(SLUT - 0.6).toFixed(3)}:d=0.6,loudnorm=I=-16:TP=-2[m];` : '';
  const slutljud = `[1:a]aformat=sample_rates=48000:channel_layouts=stereo,adelay=${Math.round(LANGD * 1000)}:all=1[o];`;
  const mix = MUSIK ? '[m][o]amix=inputs=2:normalize=0:duration=longest[mx];[mx]' : '[o]';
  execFileSync('ffmpeg', ['-v', 'error', '-y', '-i', scen, '-i', path.join(HERE, 'assets', 'spotlight-9x16.mp4'),
    ...(MUSIK ? ['-ss', start.toFixed(3), '-i', path.resolve(MUSIK)] : []), '-filter_complex',
    `[0:v][1:v]concat=n=2:v=1:a=0[v];${musik}${slutljud}${mix}loudnorm=I=-14:TP=-1.5[ao]`, '-map', '[v]', '-map', '[ao]',
    '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart', path.join(RES, fil)]);
  execFileSync('ffmpeg', ['-v', 'error', '-i', path.join(RES, fil), '-f', 'null', '-']);   // leveransfilen ska gå att avkoda
  const tider = [0.1, 0.5, 1.0, 1.8, 3.0, 5.0, LANGD - 0.1, LANGD + 1.1];
  execFileSync('ffmpeg', ['-v', 'error', '-y', ...tider.flatMap(t => ['-ss', String(t), '-i', path.join(RES, fil)]), '-filter_complex',
    tider.map((_, i) => `[${i}:v]scale=360:-2,trim=end_frame=1[k${i}]`).join(';') + ';' + tider.map((_, i) => `[k${i}]`).join('') + `hstack=inputs=${tider.length}`,
    '-frames:v', '1', path.join(OUT, `kontaktkarta-${VAR[v]}.jpg`)]);
  fs.rmSync(rutor, { recursive: true, force: true });
  console.log(`${VAR[v]} klar: resultat/${kod}/${fil}`);
}
await b.close();
