// Slutmallar för Golfkuponger (Jonas 2026-11-16): den rörliga svingloggan + två fria textrader + portal(er).
// Renderas med det gemensamma skelettet (library/templates/_mall/render-bas.mjs); reglagen står i mall.json.
//   node render.mjs --lokal [--format 9x16,4x5] [--satt text2="Det brinner inne *31/12*"] [--satt effekt=studs] [--ut dir]
//   node render.mjs --json jobb.json      ({ "varden": {...}, "format": ["9x16"], "ut": "dir" })
// Äldre form (dashboard-worker.mjs och äldre anteckningar) fungerar fortfarande:
//   node render.mjs --mall alla --rad1 "Friskvårdsbidrag kvar?" --rad2 "Det brinner inne 31/12" --eff small --stil "logga=120" --ut dir
//   { "mall", "rad1", "rad2", "effekt", "stil": {...}, "ut", "format": ["9x16"] }
// Ut: <ut>/golfkuponger-slutmallar-<format>.mp4 + kontakt-<mall>-<format>.jpg och en JSON-rad på stdout med filer, längd och textmått.
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { cli, ROT } from '../_mall/render-bas.mjs';

const SVING = process.env.SLUTMALL_SVING || path.join(ROT, 'edit-renderer/outros/golfkuponger/spotlight-9x16.mp4');
const ff = a => execFileSync('ffmpeg', ['-v', 'error', '-y', ...a]);

/** Äldre jobbfil eller äldre flaggor → reglagens nycklar. */
function tolka(jobb, argv) {
  const gammal = 'rad2' in jobb || 'stil' in jobb || ['--mall', '--rad1', '--rad2', '--eff', '--stil'].some(f => argv(f) !== null);
  if (!gammal) return {};
  const stil = jobb.stil || Object.fromEntries((argv('--stil') || '').split(',').filter(Boolean).map(p => p.split('=')));
  const varden = { ...Object.fromEntries(Object.entries(stil).filter(([k, v]) => /^[a-z_]+$/.test(k) && Number.isFinite(Number(v))).map(([k, v]) => [k, Number(v)])) };
  const mall = jobb.mall || argv('--mall'), rad1 = jobb.rad1 ?? argv('--rad1'), rad2 = jobb.rad2 ?? argv('--rad2'), effekt = jobb.effekt || argv('--eff');
  if (mall) varden.mall = mall;
  if (rad1 !== null && rad1 !== undefined) varden.text1 = rad1;
  if (rad2 !== null && rad2 !== undefined) varden.text2 = rad2;
  if (effekt) varden.effekt = effekt;
  const format = jobb.format ? [].concat(jobb.format) : (argv('--format') ? argv('--format').split(',') : null);
  return { varden, format, ut: jobb.ut || argv('--ut') };
}

// Svingloggan: loggans ram i spotlight-9x16.mp4 är x 160–919, y 401–1234 (mitt x 539,5). Beskär bort tagline, skala,
// tona kanterna mot svart och lägg på med "lighten" i RGB (i YUV blev loggan rosa och fick en mörk ruta).
function videoVal({ info }) {
  const LEN = info.langd, s = info.logga.h / 833, ox = Math.round(540 - 539.5 * s), oy = Math.round(info.logga.top - 401 * s);
  const F = 'clip((1-max(abs(X/W*2-1),abs(Y/H*2-1)))/0.08,0,1)';
  return {
    inArgs: ['-i', SVING],
    utArgs: ['-filter_complex',
      `[1:v]crop=1080:1290:0:0,scale=-2:${Math.round(1290 * s / 2) * 2},format=gbrp,` +
      `geq=r='r(X,Y)*${F}':g='g(X,Y)*${F}':b='b(X,Y)*${F}',tpad=stop_mode=clone:stop_duration=${LEN}[l];` +
      `[0:v]format=gbrp,split[t0][t1];[t0][l]overlay=${ox}:${oy}:format=gbrp:eof_action=repeat[ov];` +
      `[t1][ov]blend=all_mode=lighten,format=yuv420p,trim=duration=${LEN}[v];` +
      `[1:a]aformat=sample_rates=48000:channel_layouts=stereo,apad,atrim=0:${LEN},afade=t=out:st=${(LEN - 0.5).toFixed(2)}:d=0.5[a]`,
      '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', '-r', '30',
      '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart'],
  };
}

// Leveransfilen ska gå att avkoda, och en kontaktbild visar fem ögonblick plus slutet.
function efterVideo({ fil, info, format }) {
  ff(['-i', fil, '-f', 'null', '-']);
  const LEN = info.langd, tider = [0.13, 0.33, 0.53, 0.7, 0.85].map(a => LEN * a).concat(LEN - 0.1);
  const kontakt = path.join(path.dirname(fil), `kontakt-${info.mall}-${format}.jpg`);
  ff([...tider.flatMap(t => ['-ss', t.toFixed(2), '-i', fil]), '-filter_complex',
    tider.map((_, i) => `[${i}:v]scale=300:-2,trim=end_frame=1[k${i}]`).join(';') + ';' + tider.map((_, i) => `[k${i}]`).join('') + `hstack=inputs=${tider.length}`,
    '-frames:v', '1', kontakt]);
  console.error(`${format}: ${LEN} s, effekt ${info.effekt}, rubrik ${info.rubrik_px} px på ${info.rubrik_rader} rad(er), botten y ${info.botten}`);
  return { kontakt };
}

function svar(filer) {
  const f = filer[0] || {};
  return { mall: f.mall, rad1: f.r1, rad2: f.r2, filer };
}

if (!fs.existsSync(SVING)) throw new Error(`svingloggan saknas: ${SVING}`);
await cli(import.meta.url, { tolka, videoVal, efterVideo, svar });
