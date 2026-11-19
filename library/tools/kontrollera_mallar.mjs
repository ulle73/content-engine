#!/usr/bin/env node
// Sidkontrollen för dashboardmallar (mall/v1). Öppnar varje mallsida i Chrome och stoppar om
//   klar      sidan inte blir window.KLAR inom gränsen (eller kraschar när den startar)
//   reglage   ett reglage i mall.json aldrig läses av sidan
//   slump     samma t ger olika bild (i samma sida, baklänges eller i en ny sida)
//   zon       text eller [data-zon]-element hamnar i plattformens osäkra zon (edit-renderer/src/safezones.js)
//   referens  bilden skiljer sig mer än 0,5 % av pixlarna från referens/<format>.png
//
//   node library/tools/kontrollera_mallar.mjs                       alla mallar (library/templates/*/mall.json + testmallen)
//   node library/tools/kontrollera_mallar.mjs library/templates/x   bara de mallarna
//   --sjalvtest            dessutom: trasiga varianter av testmallen måste stoppas (körs i CI)
//   --uppdatera-referens   skriv om referensbilderna i stället för att jämföra (titta på dem innan du committar)
// Bevis (skärmbilder, diffbilder) hamnar i work/mallkontroll/.
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { ROT, KLAR_GRANS_MS, startaServer, startaWebblasare, oppnaSida, ritaRuta, lasMall } from '../templates/_mall/render-bas.mjs';

const { checkSafeZones } = await import(pathToFileURL(path.join(ROT, 'edit-renderer/src/safezones.js')).href);
const FORMAT_NYCKEL = { '9x16': '9:16', '4x5': '4:5', '1x1': '1:1', '16x9': '16:9' };
const MALLAR = path.join(ROT, 'library', 'templates');
const TESTMALL = path.join(MALLAR, '_mall', 'testmall');
const BEVIS = path.join(ROT, 'work', 'mallkontroll');
const REF_ANDEL = 0.005;      // högst 0,5 % ändrade pixlar
const REF_TROSKEL = 40;       // en pixel räknas som ändrad när någon kanal skiljer mer än så (0–255)

const args = process.argv.slice(2);
const SJALVTEST = args.includes('--sjalvtest');
const UPPDATERA = args.includes('--uppdatera-referens');

function allaMallar() {
  const ut = [];
  for (const d of fs.readdirSync(MALLAR, { withFileTypes: true })) {
    if (d.isDirectory() && fs.existsSync(path.join(MALLAR, d.name, 'mall.json'))) ut.push(path.join(MALLAR, d.name));
  }
  return [...ut.sort(), TESTMALL];
}

const sha = buf => crypto.createHash('sha1').update(buf).digest('hex').slice(0, 12);

function tider(mall, info) {
  if (mall.typ !== 'video') return [0];
  const L = info.langd, steg = 1 / (info.fps || 30);
  return [0, L * 0.25, L * 0.5, L * 0.75, Math.max(0, L - steg)].map(t => Math.round(t * 1000) / 1000);
}

async function rutor(page) {
  return page.evaluate(() => {
    const ut = [];
    const synlig = el => el.checkVisibility ? el.checkVisibility({ opacityProperty: true, visibilityProperty: true }) : true;
    const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    while (w.nextNode()) {
      const n = w.currentNode, el = n.parentElement;
      if (!n.textContent.trim() || !el || el.closest('[data-zon-ignorera]') || el.closest('script,style') || !synlig(el)) continue;
      const r = document.createRange(); r.selectNodeContents(n);
      for (const b of r.getClientRects()) if (b.width > 0 && b.height > 0) ut.push({ id: `"${n.textContent.trim().slice(0, 24)}"`, x: b.x, y: b.y, w: b.width, h: b.height });
    }
    for (const el of document.querySelectorAll('[data-zon]')) {
      if (el.closest('[data-zon-ignorera]') || !synlig(el)) continue;
      const b = el.getBoundingClientRect();
      ut.push({ id: el.dataset.zon || el.id || el.tagName.toLowerCase(), x: b.x, y: b.y, w: b.width, h: b.height });
    }
    for (const b of window.INFO?.rutor || []) ut.push(b);
    return ut;
  });
}

async function jamforBilder(browser, aPng, bPng) {
  const p = await browser.newPage();
  try {
    return await p.evaluate(async ([a, b, troskel]) => {
      const las = src => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = src; });
      const [ia, ib] = await Promise.all([las(a), las(b)]);
      if (ia.width !== ib.width || ia.height !== ib.height) return { andel: 1, storlek: `${ia.width}×${ia.height} mot ${ib.width}×${ib.height}` };
      const c = n => { const k = document.createElement('canvas'); k.width = ia.width; k.height = ia.height; return k; };
      const ca = c(), cb = c(), cd = c();
      ca.getContext('2d').drawImage(ia, 0, 0); cb.getContext('2d').drawImage(ib, 0, 0);
      const da = ca.getContext('2d').getImageData(0, 0, ia.width, ia.height).data, db = cb.getContext('2d').getImageData(0, 0, ia.width, ia.height).data;
      const dctx = cd.getContext('2d'); dctx.globalAlpha = 0.35; dctx.drawImage(ib, 0, 0); dctx.globalAlpha = 1;
      const diff = dctx.getImageData(0, 0, ia.width, ia.height); let n = 0;
      for (let i = 0; i < da.length; i += 4) {
        if (Math.max(Math.abs(da[i] - db[i]), Math.abs(da[i + 1] - db[i + 1]), Math.abs(da[i + 2] - db[i + 2])) > troskel) {
          n++; diff.data[i] = 255; diff.data[i + 1] = 0; diff.data[i + 2] = 80; diff.data[i + 3] = 255;
        }
      }
      dctx.putImageData(diff, 0, 0);
      return { andel: n / (da.length / 4), diff: cd.toDataURL('image/png') };
    }, [`data:image/png;base64,${aPng.toString('base64')}`, `data:image/png;base64,${bPng.toString('base64')}`, REF_TROSKEL]);
  } finally { await p.close(); }
}

const ZON_SV = { top: 'övre', bottom: 'nedre', left: 'vänstra', right: 'högra' };

/** Kontrollerar en mall i alla dess format. Returnerar { fel: [{kod, text}], matt: [{mall, format, klarMs}] }. */
export async function kontrollera(browser, server, mallDir, { urlMapp, namn, grans = KLAR_GRANS_MS } = {}) {
  const fel = [], matt = [];
  let mall;
  try { mall = lasMall(mallDir); } catch (e) { return { fel: [{ kod: 'mall', text: e.message }], matt }; }
  namn ||= mall.id;
  fs.mkdirSync(BEVIS, { recursive: true });
  for (const format of mall.format) {
    const fmt = `${namn} ${format}`;
    let s1;
    try { s1 = await oppnaSida(browser, server, mallDir, { format, mall, urlMapp, grans }); }
    catch (e) { fel.push({ kod: 'klar', text: `${fmt}: ${e.message}` }); continue; }
    const { page, info, klarMs } = s1;
    matt.push({ mall: namn, format, klarMs });
    const T = tider(mall, info), bilder = {};
    try {
      // slump: samma t ska ge samma bild framlänges, baklänges och (nedan) i en ny sida
      for (const t of T) { await ritaRuta(page, t); bilder[t] = await page.screenshot({ type: 'png' }); }
      for (const t of [...T].reverse()) {
        await ritaRuta(page, t);
        if (sha(await page.screenshot({ type: 'png' })) !== sha(bilder[t])) { fel.push({ kod: 'slump', text: `${fmt}: t=${t} gav en annan bild andra gången i samma sida` }); break; }
      }
      // zon: text och [data-zon] vid varje kontrolltid
      for (const t of T) {
        await ritaRuta(page, t);
        for (const b of checkSafeZones(await rutor(page), FORMAT_NYCKEL[format])) {
          fel.push({ kod: 'zon', text: `${fmt} t=${t}: ${b.id} går ${b.px} px in i den ${ZON_SV[b.zone]} osäkra zonen` });
        }
      }
      // reglage: varje reglage ska läsas av sidan
      const lasta = new Set(await page.evaluate(() => [...(window.__mallLasta || [])]));
      const olasta = mall.reglage.map(r => r.nyckel).filter(k => !lasta.has(k));
      if (olasta.length) fel.push({ kod: 'reglage', text: `${fmt}: sidan läser aldrig ${olasta.join(', ')}, så reglaget gör ingenting` });
      for (const v of info.varningar || []) console.error(`  varning ${fmt}: ${v}`);
    } finally { await page.close(); }

    try {
      const { page: p2 } = await oppnaSida(browser, server, mallDir, { format, mall, urlMapp, grans });
      try {
        for (const t of T) {
          await ritaRuta(p2, t);
          if (sha(await p2.screenshot({ type: 'png' })) !== sha(bilder[t])) { fel.push({ kod: 'slump', text: `${fmt}: t=${t} gav en annan bild i en ny sida` }); break; }
        }
      } finally { await p2.close(); }
    } catch (e) { fel.push({ kod: 'klar', text: `${fmt} (andra öppningen): ${e.message}` }); }

    // referens: bilden vid t=0 (stillbild) eller mitt i filmen
    const tRef = T[mall.typ === 'video' ? 2 : 0], bild = bilder[tRef];
    const refFil = path.join(mallDir, 'referens', `${format}.png`);
    fs.writeFileSync(path.join(BEVIS, `${namn}-${format}.png`), bild);
    if (UPPDATERA && !urlMapp) {
      fs.mkdirSync(path.dirname(refFil), { recursive: true });
      fs.writeFileSync(refFil, bild);
      console.error(`  referens skriven: ${path.relative(ROT, refFil)}`);
    } else if (!fs.existsSync(refFil)) {
      fel.push({ kod: 'referens', text: `${fmt}: referensbild saknas (${path.relative(ROT, refFil)}); kör med --uppdatera-referens och titta på bilden` });
    } else {
      const j = await jamforBilder(browser, bild, fs.readFileSync(refFil));
      if (j.diff) fs.writeFileSync(path.join(BEVIS, `${namn}-${format}-diff.png`), Buffer.from(j.diff.split(',')[1], 'base64'));
      if (j.andel > REF_ANDEL) {
        fel.push({ kod: 'referens', text: `${fmt}: ${(j.andel * 100).toFixed(2)} % av pixlarna skiljer från referensen (högst ${REF_ANDEL * 100} %)` +
          (j.storlek ? `, storlek ${j.storlek}` : `; se work/mallkontroll/${namn}-${format}-diff.png`) });
      }
    }
  }
  return { fel, matt };
}

// Självtestet: varje variant är testmallen med ett fel, och kontrollen måste stoppa den med rätt kod.
const VARIANTER = [
  { namn: 'utan-klar', kod: 'klar', sida: ['forbered(v, ctx) {', 'async forbered(v, ctx) { await new Promise(() => {});'] },
  { namn: 'slump', kod: 'slump', sida: ['rita() { /* stillbild: allt ritas i forbered */ },',
    "rita() { document.querySelector('#etikett').style.transform = 'translateX(' + Math.round(Math.random() * 80) + 'px)'; },"] },
  { namn: 'utanfor-zon', kod: 'zon', sida: ['rita() { /* stillbild: allt ritas i forbered */ },', "rita() { document.querySelector('#bana').style.top = '12px'; },"] },
  { namn: 'olast-reglage', kod: 'reglage', mall: m => { m.reglage.push({ nyckel: 'oanvand', typ: 'avpa', etikett: 'Används inte', standard: false }); } },
  { namn: 'ny-farg', kod: 'referens', mall: m => { m.reglage.find(r => r.nyckel === 'etikett_farg').standard = '#ff3b30'; } },
];

async function sjalvtest(browser) {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'mallprov-'));
  const extra = {}, kopior = [];
  try {
    for (const v of VARIANTER) {
      const mapp = path.join(tmp, v.namn);
      fs.cpSync(TESTMALL, mapp, { recursive: true });
      if (v.sida) {
        const f = path.join(mapp, 'sida.html'), html = fs.readFileSync(f, 'utf8');
        if (!html.includes(v.sida[0])) throw new Error(`självtestet ${v.namn}: hittar inte "${v.sida[0]}" i testmallens sida.html`);
        fs.writeFileSync(f, html.replace(v.sida[0], v.sida[1]));
      }
      if (v.mall) {
        const f = path.join(mapp, 'mall.json'), m = JSON.parse(fs.readFileSync(f, 'utf8'));
        v.mall(m); fs.writeFileSync(f, JSON.stringify(m, null, 2));
      }
      const urlMapp = `/library/templates/_mall/${v.namn}/`;
      extra[urlMapp] = mapp;
      kopior.push({ ...v, mapp, urlMapp });
    }
    const server = await startaServer({ extra });
    const misslyckade = [];
    try {
      for (const v of kopior) {
        const { fel } = await kontrollera(browser, server, v.mapp, { urlMapp: v.urlMapp, namn: `sjalvtest-${v.namn}`, grans: 4000 });
        const stoppad = fel.some(f => f.kod === v.kod);
        console.log(`${stoppad ? '✓' : '✗'} självtest ${v.namn}: ${stoppad ? `stoppad (${v.kod})` : `INTE stoppad, väntade ${v.kod}; fick ${fel.map(f => f.kod).join(', ') || 'inga fel'}`}`);
        if (!stoppad) misslyckade.push(v.namn);
      }
    } finally { await server.stang(); }
    return misslyckade;
  } finally { fs.rmSync(tmp, { recursive: true, force: true }); }
}

async function main() {
  const valda = args.filter(a => !a.startsWith('--')).map(a => path.resolve(a));
  const mappar = valda.length ? valda : allaMallar();
  const browser = await startaWebblasare();
  const server = await startaServer();
  let antalFel = 0;
  try {
    for (const mapp of mappar) {
      const { fel, matt } = await kontrollera(browser, server, mapp);
      const id = path.relative(ROT, mapp).split(path.sep).join('/');
      for (const m of matt) console.log(`  ${id} ${m.format}: KLAR efter ${m.klarMs} ms`);
      if (fel.length) { antalFel += fel.length; console.log(`✗ ${id}`); for (const f of fel) console.log(`    [${f.kod}] ${f.text}`); }
      else console.log(`✓ ${id}`);
    }
    if (SJALVTEST) {
      const misslyckade = await sjalvtest(browser);
      if (misslyckade.length) { antalFel += misslyckade.length; console.log(`✗ självtestet släppte igenom: ${misslyckade.join(', ')}`); }
    }
  } finally {
    await server.stang();
    await browser.close();
  }
  console.log(antalFel ? `${antalFel} fel` : 'alla mallar godkända');
  process.exit(antalFel ? 1 : 0);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) await main();