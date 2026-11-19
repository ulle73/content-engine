// Sidkontraktet för dashboardmallar (mall/v1). En mallsida importerar starta() och beskriver bara sitt eget utseende:
//
//   import { starta } from '../_mall/sida.mjs';
//   starta({
//     forbered(v, ctx) { ... },   // bygg sidan för värdena v (anropas igen när värdena ändras i förhandsvisningen)
//     rita(t, v, ctx) { ... },    // rita exakt tiden t i sekunder; samma t ska alltid ge samma bild
//     info(v, ctx) { return { langd: 0 } },   // valfri: längd i sekunder (video) och egna varningar
//   });
//
// Hjälpen sköter resten av kontraktet:
//   In    window.PARAMS (sätts av renderaren före sidans skript, eller med postMessage från samma adress). Saknas ett
//         värde används standard_per och sedan standard ur mall.json, som läses bredvid sidan. Tal kläms mot min/max.
//   Klar  window.KLAR = true när typsnitt, bilder och video har laddats och första bildrutan är ritad.
//   Ruta  window.frame(t)
//   Ut    window.INFO = { mall, format, bredd, hojd, langd, fps, varningar, ... }
// visa_zoner: true i PARAMS ritar plattformarnas osäkra zoner ovanpå (edit-renderer/src/safezones.js).
import { FORMATS, unsafeRects } from '../../../edit-renderer/src/safezones.js';

const FORMAT_NYCKEL = { '9x16': '9:16', '4x5': '4:5', '1x1': '1:1', '16x9': '16:9' };

export function formatInfo(format) {
  const nyckel = FORMAT_NYCKEL[format];
  if (!nyckel) throw new Error(`okänt format: ${format}`);
  const { W, H, safe } = FORMATS[nyckel];
  return { format, nyckel, bredd: W, hojd: H, marginal: safe, osakra: unsafeRects(nyckel) };
}

/** Värdena för ett format: PARAMS → standard_per → standard, klämda mot gränserna i mall.json. */
export function losVarden(mall, params = {}, format) {
  const per = mall.standard_per?.format?.[format] || {};
  const v = {};
  for (const r of mall.reglage) {
    const k = r.nyckel;
    let x = k in params ? params[k] : (k in per ? per[k] : r.standard);
    if (r.typ === 'tal') {
      x = Number(x);
      if (!Number.isFinite(x)) x = Number(k in per ? per[k] : r.standard);
      x = Math.min(r.max, Math.max(r.min, x));
    } else if (r.typ === 'text') {
      x = String(x ?? '').slice(0, r.max_langd);
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
    let senasteT = 0, ctx, v;
    const uppdatera = async (params) => {
      const format = mall.format.includes(params.format) ? params.format : mall.format[0];
      const fi = formatInfo(format);
      document.documentElement.style.setProperty('--bredd', fi.bredd + 'px');
      document.documentElement.style.setProperty('--hojd', fi.hojd + 'px');
      Object.assign(document.body.style, { width: fi.bredd + 'px', height: fi.hojd + 'px', margin: '0', overflow: 'hidden', position: 'relative' });
      ctx = { mall, ...fi };
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
    await uppdatera(window.PARAMS || fragaParams());
    // Förhandsvisningen i dashboarden skickar nya värden; bara från samma adress.
    window.addEventListener('message', async (e) => {
      if (e.origin !== location.origin || e.data?.typ !== 'mall-params') return;
      window.KLAR = false;
      window.PARAMS = e.data.params || {};
      await uppdatera(window.PARAMS);
      window.KLAR = true;
    });
    window.KLAR = true;
  } catch (err) {
    window.MALLFEL = String(err?.stack || err);
    console.error('mallen kunde inte starta:', err);
  }
}
