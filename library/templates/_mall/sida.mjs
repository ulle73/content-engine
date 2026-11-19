// Sidkontraktet för dashboardmallar (mall/v1). En mallsida importerar starta() och beskriver bara sitt eget utseende:
//
//   import { starta } from '../_mall/sida.mjs';
//   starta({
//     forbered(v, ctx) { ... },   // bygg sidan för värdena v (anropas igen när värdena ändras i förhandsvisningen)
//     rita(t, v, ctx) { ... },    // rita exakt tiden t i sekunder; samma t ska alltid ge samma bild
//     info(v, ctx) { return { langd: 0 } },   // valfri: längd i sekunder (video) och egna varningar
//     forstaT: 0,                 // valfri: tiden som ritas först (t.ex. sista bildrutan i en förhandsvisning)
//     fraga(q) { return {...} },  // valfri: översätt äldre adressparametrar till reglagens nycklar
//   });
//
// Hjälpen sköter resten av kontraktet:
//   In    window.PARAMS (sätts av renderaren före sidans skript, eller med postMessage från samma adress). Saknas ett
//         värde används standard_per och sedan standard ur mall.json, som läses bredvid sidan. Tal kläms mot min/max.
//   Klar  window.KLAR = true när typsnitt, bilder och video har laddats och första bildrutan är ritad.
//   Ruta  window.frame(t)
//   Ut    window.INFO = { mall, format, bredd, hojd, langd, fps, varningar, ... }
// visa_zoner: true i PARAMS ritar plattformarnas osäkra zoner ovanpå (edit-renderer/src/safezones.js).
// safezones.js serveras bredvid den här filen (render-bas.mjs och Django pekar _mall/safezones.js på
// edit-renderer/src/safezones.js), så att sidan aldrig behöver gå upp ur library/templates.
import { FORMATS, unsafeRects } from './safezones.js';

const FORMAT_NYCKEL = { '9x16': '9:16', '4x5': '4:5', '1x1': '1:1', '16x9': '16:9' };

export function formatInfo(format) {
  const nyckel = FORMAT_NYCKEL[format];
  if (!nyckel) throw new Error(`okänt format: ${format}`);
  const { W, H, safe } = FORMATS[nyckel];
  return { format, nyckel, bredd: W, hojd: H, marginal: safe, osakra: unsafeRects(nyckel) };
}

/** Standardvärdet för varje reglage: standard, sedan standard_per (format först, sedan övriga i ordning). */
export function standardvarden(mall, format, valda = {}) {
  const std = Object.fromEntries(mall.reglage.map(r => [r.nyckel, r.standard]));
  const per = mall.standard_per || {};
  Object.assign(std, per.format?.[format] || {});
  for (const [beror, perVal] of Object.entries(per)) {
    if (beror === 'format') continue;
    const x = beror in valda ? valda[beror] : std[beror];
    const over = { ...(perVal[String(x)] || {}) };
    delete over[beror];
    Object.assign(std, over);
  }
  return std;
}

/** Värdena för ett format: PARAMS → standard_per → standard, klämda mot gränserna i mall.json. */
export function losVarden(mall, params = {}, format) {
  // de reglage som andra beror på (t.ex. effekt) avgörs först, så att deras standard_per kan användas
  const valda = {};
  for (const beror of Object.keys(mall.standard_per || {})) if (beror in params) valda[beror] = params[beror];
  const per = standardvarden(mall, format, valda);
  const v = {};
  for (const r of mall.reglage) {
    const k = r.nyckel;
    let x = k in params ? params[k] : per[k];
    if (r.typ === 'tal') {
      x = Number(x);
      if (!Number.isFinite(x)) x = Number(per[k]);
      x = Math.min(r.max, Math.max(r.min, x));
    } else if (r.typ === 'text') {
      x = String(x ?? '').slice(0, r.max_langd);
      if (r.kravs && !x.trim()) x = String(per[k] ?? '');
    } else if (r.typ === 'val' || r.typ === 'typsnitt') {
      if (!r.val.some(o => o.varde === x)) x = r.standard;
    } else if (r.typ === 'farg') {
      if (!/^#[0-9a-f]{6}$/i.test(String(x))) x = r.standard;
    } else if (r.typ === 'avpa') {
      x = x === true || x === 'true' || x === 1 || x === '1';
    } else if (r.typ === 'bild') {
      x = typeof x === 'string' && x ? x : null;
    }
    v[k] = x;
  }
  return v;
}

// Kontrollen (library/tools/kontrollera_mallar.mjs) läser vilka reglage sidan faktiskt använder.
const lasta = (window.__mallLasta = new Set());
function sparad(v) {
  return new Proxy(v, { get(o, k) { if (typeof k === 'string') lasta.add(k); return o[k]; } });
}

function fragaParams() {
  // Fristående öppning: ?format=4x5&visa_zoner=1&rubrik=Hej (bara för provning; renderaren använder window.PARAMS).
  const q = new URLSearchParams(location.search), p = {};
  for (const [k, x] of q) p[k] = x;
  return p;
}

async function vantaMedia() {
  await document.fonts.ready;
  const bilder = [...document.images].filter(i => i.src && !i.complete);
  await Promise.all(bilder.map(i => new Promise(r => { i.onload = i.onerror = r; })));
  await Promise.all([...document.images].map(i => (i.decode ? i.decode().catch(() => {}) : null)));
  const filmer = [...document.querySelectorAll('video')].filter(f => f.readyState < 2);
  await Promise.all(filmer.map(f => new Promise(r => { f.addEventListener('loadeddata', r, { once: true }); f.addEventListener('error', r, { once: true }); })));
}

function ritaZoner(fi) {
  document.getElementById('mall-zoner')?.remove();
  const lager = document.createElement('div');
  lager.id = 'mall-zoner';
  lager.dataset.zonIgnorera = '';
  lager.style.cssText = `position:fixed;left:0;top:0;width:${fi.bredd}px;height:${fi.hojd}px;pointer-events:none;z-index:2147483647`;
  for (const r of fi.osakra) {
    const d = document.createElement('div');
    d.style.cssText = `position:absolute;left:${r.x0}px;top:${r.y0}px;width:${r.x1 - r.x0}px;height:${r.y1 - r.y0}px;` +
      'background:rgba(255,0,80,.22);outline:1px dashed rgba(255,0,80,.8)';
    lager.appendChild(d);
  }
  document.body.appendChild(lager);
}

export async function starta(sida) {
  try {
    const mall = await (await fetch(new URL('mall.json', location.href))).json();
    let senasteT = Number(sida.forstaT) || 0, ctx, v;
    // Förhandsvisningen i dashboarden skickar nya värden, bara från samma adress. Lyssnaren finns från start så att
    // inget meddelande går förlorat medan sidan laddar; det senaste värdet vinner.
    let startad = false, vantande = null, kor = Promise.resolve();
    const nya = (params) => (kor = kor.then(async () => {
      window.KLAR = false;
      window.PARAMS = params;
      await uppdatera(params);
      window.KLAR = true;
    }));
    window.addEventListener('message', (e) => {
      if (e.origin !== location.origin || e.data?.typ !== 'mall-params') return;
      window.KLAR = false;
      if (startad) nya(e.data.params || {}); else vantande = e.data.params || {};
    });
    const uppdatera = async (params) => {
      const format = mall.format.includes(params.format) ? params.format : mall.format[0];
      const fi = formatInfo(format);
      document.documentElement.style.setProperty('--bredd', fi.bredd + 'px');
      document.documentElement.style.setProperty('--hojd', fi.hojd + 'px');
      Object.assign(document.body.style, { width: fi.bredd + 'px', height: fi.hojd + 'px', margin: '0', overflow: 'hidden', position: 'relative' });
      ctx = { mall, ...fi, params };
      v = sparad(losVarden(mall, params, format));
      await sida.forbered?.(v, ctx);
      await vantaMedia();
      const egen = (await sida.info?.(v, ctx)) || {};
      window.INFO = {
        mall: mall.id, format, bredd: fi.bredd, hojd: fi.hojd,
        langd: mall.typ === 'video' ? Number(egen.langd) || 0 : 0,
        fps: mall.video?.fps || 30,
        ...egen,
        varningar: [...(egen.varningar || [])],
      };
      await window.frame(senasteT);
      if (params.visa_zoner === true || params.visa_zoner === 'true' || params.visa_zoner === '1') ritaZoner(fi);
      else document.getElementById('mall-zoner')?.remove();
    };
    window.frame = async (t) => {
      senasteT = Number(t) || 0;
      await sida.rita(senasteT, v, ctx);
    };
    // sida.fraga(q) låter en äldre sida översätta sina gamla adressparametrar till reglagens nycklar
    const q = new URLSearchParams(location.search);
    await uppdatera(window.PARAMS || (sida.fraga ? sida.fraga(q) : fragaParams()));
    startad = true;
    window.KLAR = true;
    if (vantande) await nya(vantande);
  } catch (err) {
    window.MALLFEL = String(err?.stack || err);
    console.error('mallen kunde inte starta:', err);
  }
}
