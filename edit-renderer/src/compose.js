// Build a HyperFrames project (index.html + assets + fonts) from a cut spec (cut/v1) with the generic cut template.
// Finish layer: beat-snapped timing, designed typography (type scale, balanced Swedish line breaks, bundled fonts),
// platform safe zones, a per-brand look (grade, grain, vignette, always-moving camera, motion blur), legibility
// treatment from the measured picture, and the SFX cue sheet for finish.js.
import { copyFileSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, extname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { alignToBeat, snapScenes } from './beats.js';
import { legibility } from './legibility.js';
import { FORMATS, PLATFORM_ZONES } from './safezones.js';
import { TRANSITION_SFX } from './sfx.js';
import { SUPPORT, resolve, transitionDuration } from './support.js';
import {
  FONTS_DIR, FONT_FACES, GLUE_WORDS, breakLines, fontFiles, isGlue, maxChars, metrics, resolveBrandFonts, sizeSteps,
} from './typeset.js';

export { FORMATS };

const HERE = dirname(fileURLToPath(import.meta.url));
const RUNTIME = readFileSync(join(HERE, 'runtime.js'), 'utf8');
export const GSAP_URL = 'https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js';

const HARD_SWAPS = new Set(['cut', 'flash', 'glitch', 'speed-ramp']);
const BLUR_TRANSITIONS = { whip: 'x', push: 'y', 'speed-ramp': 'x' };
const CAMERAS = ['ken-burns', 'push-in', 'pull-back'];
const CHAR_STYLES = new Set(['typewriter', 'cascade', 'scramble', 'tracking-in']);
const MASK_STYLES = new Set(['rise', 'line-reveal', 'highlight', 'shimmer', 'lower-third']);
const DISPLAY_STYLES = new Set(['slam', 'extrusion', 'caption', 'chunk']);
const LT_PAD = 92; // .lt horizontal padding (40 + 52)
const DEFAULT_BRAND = { background: '#111814', foreground: '#ffffff', accent: '#68766f', muted: '#dfe7e3', paper: '#f6f8f7', ink: '#111814' };

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const r3 = (n) => Math.round(n * 1000) / 1000;
const fmtS = (n) => (Math.round(n * 10) / 10).toFixed(1).replace(".", ",");
const hex = (c, fallback) => (/^#[0-9a-fA-F]{6}$/.test(String(c || '')) ? String(c).toLowerCase() : fallback);

function rgb(h) {
  return [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
}
function mix(a, b, t) {
  const [x, y] = [rgb(a), rgb(b)];
  return '#' + x.map((v, i) => Math.round(v + (y[i] - v) * t).toString(16).padStart(2, '0')).join('');
}
function luminance(h) {
  const [r, g, b] = rgb(h).map((v) => { const s = v / 255; return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4; });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
function rgba(h, a) {
  const [r, g, b] = rgb(h);
  return `rgba(${r}, ${g}, ${b}, ${a})`;
}

/** "Kort *betonad* text" → [{text, em}] words. */
export function words(text) {
  const out = [];
  let em = false;
  for (const part of String(text || '').split('*')) {
    for (const w of part.split(/\s+/).filter(Boolean)) out.push({ text: w, em });
    em = !em;
  }
  return out;
}

/**
 * Caption chunks: 2–3 words (≤ 16 characters), never ending on a function word or a bare number unless the chunk
 * would pass 4 words / 22 characters, always ending at a sentence end, and never a lone word at the end of a line
 * of thought ("Det är att du inte ser / den.").
 */
export function chunkWords(list) {
  const out = [];
  let cur = [];
  const len = (arr) => arr.reduce((s, w) => s + w.text.length, 0) + Math.max(0, arr.length - 1);
  const ends = (w) => /[.!?:;…]["”»)]*$/.test(w.text);
  for (const w of list) {
    if (cur.length) {
      const last = cur[cur.length - 1];
      const full = cur.length >= 3 || len([...cur, w]) > 16;
      const hard = cur.length >= 4 || len([...cur, w]) > 22;
      if (ends(last) || hard || (full && !isGlue(last.text))) {
        out.push(cur);
        cur = [];
      }
    }
    cur.push(w);
  }
  if (cur.length) {
    // Fold a lone trailing word into the previous chunk when it still reads as one phrase.
    const prev = out[out.length - 1];
    if (cur.length === 1 && prev && !ends(prev[prev.length - 1]) && len([...prev, ...cur]) <= 22) prev.push(...cur);
    else out.push(cur);
  }
  return out;
}

function wordHtml(w, i, style, mark) {
  const inner = CHAR_STYLES.has(style)
    ? [...w.text].map((ch) => `<span class="ch">${esc(ch)}</span>`).join('')
    : esc(w.text);
  const em = w.em || i === mark;
  const marker = style === 'highlight' && em ? '<span class="mk"></span>' : '';
  return `<span class="w${em ? ' em' : ''}" data-layout-allow-overflow>${marker}<span class="wi">${inner}</span></span>`;
}

function wordsHtml(list, style) {
  const mark = style === 'highlight' && !list.some((w) => w.em) && list.length ? list.length - 1 : -1;
  if (style === 'chunk') {
    let k = 0;
    return chunkWords(list).map((c) => `<span class="ck">${c.map((w) => wordHtml(w, k++, style, mark)).join(' ')}</span>`).join('');
  }
  return list.map((w, i) => wordHtml(w, i, style, mark)).join(' ');
}

/**
 * Reading time. Swedish TV subtitles follow 12 characters per second, spaces and punctuation included (SVT: one line
 * 2–4 s, two lines 4–6 s); Netflix's Swedish ceiling is 17 cps and no text event is shorter than 5/6 s; BBC: at least
 * ~0.3 s per word. Viewers of an ad also watch the picture, so the default is the Swedish 12 cps.
 * EDIT_READ_CPS overrides it.
 */
export const READ = {
  cps: Number(process.env.EDIT_READ_CPS) > 0 ? Number(process.env.EDIT_READ_CPS) : 12,
  minEvent: 5 / 6,
  // Entrance after the transition (~0.15–0.5 s), the clean exit before the next scene (~0.3 s) and a little air:
  // measured in the faiv-winter-mood test, 0.6 s left the shortest chunk at 0.75 s, under the 5/6 s floor.
  overhead: 0.9,
};

/** Seconds one piece of on-screen text needs to be read (spaces and punctuation count, *emphasis* marks do not). */
export function readSeconds(text) {
  const chars = String(text || '').replace(/\*/g, '').trim().length;
  return chars ? Math.max(READ.minEvent, chars / READ.cps) : 0;
}

/** Seconds a scene needs for its text in a given style (chunk captions are read piece by piece). */
export function sceneReadSeconds(text, style) {
  const list = words(text);
  if (!list.length) return 0;
  let pieces;
  if (style === 'chunk') pieces = chunkWords(list).map((c) => c.map((w) => w.text).join(' '));
  else if (style === 'caption') pieces = list.map((w) => w.text);
  else pieces = [list.map((w) => w.text).join(' ')];
  const minPiece = style === 'caption' ? 0.3 : READ.minEvent;  // word by word: BBC's ~0.3 s per word
  return pieces.reduce((s, p) => s + Math.max(minPiece, p.length / READ.cps), 0) + READ.overhead;
}

function sfxOf(native) {
  return SUPPORT.effects[native]?.sfx || null;
}

function plan(spec, files, warnings, { grid, logo }) {
  const raw = spec.scenes.map((s, idx) => {
    const where = `Scen ${s.id}`;
    let transition = null;
    if (idx > 0 && s.transition_in) {
      const native = resolve('transitions', s.transition_in);
      if (!native) warnings.push(`${where}: övergången ${s.transition_in} stöds inte av klippmallen; hårt klipp används.`);
      else transition = { type: native, d: transitionDuration(native), cut: HARD_SWAPS.has(native) };
    }
    const natives = [];
    for (const id of s.effects || []) {
      const native = resolve('effects', id);
      if (!native) warnings.push(`${where}: effekten ${id} stöds inte av klippmallen och hoppades över.`);
      else if (!natives.includes(native)) natives.push(native);
    }
    const cams = natives.filter((n) => CAMERAS.includes(n));
    if (cams.length > 1) warnings.push(`${where}: flera kamerarörelser (${cams.join(', ')}); bara ${cams[0]} används.`);
    const grades = natives.filter((n) => n.startsWith('grade-'));
    if (grades.length > 1) warnings.push(`${where}: flera graderingar; bara ${grades[0]} används.`);
    if (!logo && natives.some((n) => n.startsWith('logo-'))) warnings.push(`${where}: logo-effekten kräver en logga i varumärket och hoppades över.`);
    const file = files[s.asset_id];
    if (!file) throw new Error(`Mediefil saknas för ${where}`);
    // Never a static frame: stills get Ken Burns, video a slow eased push.
    const camera = cams[0] || (file.kind === 'image' ? 'ken-burns' : 'micro-push');
    let style = null;
    if (s.text) {
      style = resolve('text', s.text_style);
      if (s.text_style && !style) warnings.push(`${where}: textstilen ${s.text_style} stöds inte av klippmallen; standardstilen används.`);
      const captionLook = natives.map((n) => SUPPORT.effects[n]?.text_style).find(Boolean);
      style = style || captionLook || (s.purpose === 'hook' ? 'slam' : 'rise');
    }
    const trim = Number(s.trim_start_s || 0);
    const maxDuration = file.kind === 'video' && file.duration ? Math.max(0.5, file.duration - trim) : undefined;
    // Text must stay long enough to be read: lengthen the scene (as far as the clip allows) instead of rushing it.
    let duration = Number(s.duration_s);
    const need = s.text ? r3(sceneReadSeconds(s.text, style)) : 0;
    if (need > duration + 0.05) {
      const longer = r3(Math.min(need, maxDuration ?? need));
      if (longer > duration + 0.05) {
        warnings.push(`${where}: förlängd från ${fmtS(duration)} till ${fmtS(longer)} s så att texten hinner läsas `
          + `(${READ.cps} tecken/s).`);
        duration = longer;
      }
      if (need > longer + 0.05) {
        warnings.push(`${where}: texten behöver ${fmtS(need)} s men klippet räcker till ${fmtS(longer)} s. Korta texten `
          + 'eller välj ett längre klipp.');
      }
    }
    return {
      id: s.id, idx, duration, transition, natives, camera, grade: grades[0] || null, style,
      kind: file.kind, file, source: s, minDuration: Math.min(need, duration),
      maxDuration,
      position: style === 'lower-third' ? 'bottom' : s.text_position || (s.purpose === 'hook' || s.purpose === 'cta' ? 'center' : 'bottom'),
    };
  });
  // Beat sync: move scene boundaries (and with them the transitions) onto the music's beats.
  let timing = null;
  if (grid) {
    const snapped = snapScenes(raw.map((r) => ({ id: r.id, duration: r.duration, max: r.maxDuration, min: r.minDuration })), grid);
    snapped.durations.forEach((d, i) => { raw[i].duration = d; });
    timing = snapped;
  }
  const scenes = [];
  let clock = 0;
  for (const r of raw) {
    scenes.push({ ...r, start: r3(clock), end: r3(clock + r.duration) });
    clock += r.duration;
  }
  // Clamp each transition to what the two neighbouring scenes can carry.
  scenes.forEach((s, i) => {
    if (!s.transition || !i) return;
    const room = Math.min(s.end - s.start, scenes[i - 1].end - scenes[i - 1].start) * 0.6;
    s.transition.d = r3(Math.min(s.transition.d, room));
  });
  let endcard = null;
  if (spec.cta) {
    // The end card holds logo, line and url: give the line its reading time (the url pill is read as one word).
    const duration = Math.max(Number(spec.cta.duration_s || 2.5), r3(sceneReadSeconds(spec.cta.text, 'rise') + 0.4));
    endcard = { id: 'cta', idx: scenes.length, isEnd: true, start: r3(clock), end: r3(clock + duration),
                transition: { type: 'fade', d: 0.6, cut: false } };
    clock += duration;
  }
  const total = r3(clock);
  const seq = endcard ? [...scenes, endcard] : scenes;
  seq.forEach((s, i) => {
    const t = s.transition;
    s.winStart = i && t && !t.cut ? r3(Math.max(0, s.start - t.d / 2)) : s.start;
    const next = seq[i + 1];
    s.winEnd = next && next.transition && !next.transition.cut ? r3(Math.min(total, s.end + next.transition.d / 2)) : s.end;
    // Text lands after the transition settles – on a beat when there is music.
    const base = s.start + (t && !t.cut ? t.d / 2 : 0) + (s.isEnd ? 0.1 : 0.12);
    const onBeat = grid ? alignToBeat(base, grid, { before: 0.08, after: 0.4 }) : base;
    s.textAt = r3(onBeat <= s.end - 0.7 ? onBeat : base);
  });
  if (scenes.length) scenes[scenes.length - 1].winEnd = endcard ? scenes[scenes.length - 1].winEnd : total;
  return { scenes, endcard, total, timing };
}

function mediaHtml(s, music) {
  // A per-scene fragment keeps reused stills distinct for HyperFrames' media discovery (same file, no extra bytes).
  const name = s.kind === 'image' ? `assets/${s.file.name}#${s.id}` : `assets/${s.file.name}`;
  const fit = s.source.fit === 'contain' ? 'contain' : 'cover';
  if (s.kind === 'image') {
    const bg = fit === 'contain' ? `<img class="media bgfill" src="${name}-bg" alt="">` : '';
    return `${bg}<img id="M-${s.id}" class="media fit-${fit}" src="${name}" alt="">`;
  }
  const preroll = s.start - s.winStart;
  const trim = Number(s.source.trim_start_s || 0);
  const mediaStart = Math.max(0, trim - preroll);
  let len = s.winEnd - s.winStart;
  if (s.file.duration) len = Math.min(len, Math.max(0.1, s.file.duration - mediaStart));
  const keep = s.source.audio === 'keep' || (!s.source.audio && !music);
  const sound = keep && s.file.hasAudio ? 'data-has-audio="true" data-volume="1"' : 'muted';
  return `<video id="M-${s.id}" class="media fit-${fit}" src="${name}" ${sound} playsinline data-start="${r3(s.winStart)}" `
    + `data-duration="${r3(len)}" data-media-start="${r3(mediaStart)}" data-track-index="${s.idx + 1}"></video>`;
}

/** Layout parameters for one text block (the browser runtime fits and breaks it). */
function textSpec(style, position, fmt, format, fonts, extra = {}) {
  const { W, H, safe } = fmt;
  const maxW = W - safe.left - safe.right;
  const room = H - safe.top - safe.bottom;
  const display = DISPLAY_STYLES.has(style);
  const face = display ? fonts.display : fonts.text;
  const m = metrics(style, face);
  return {
    style, face, sizes: sizeSteps(format, style, position, W, H), leading: m.leading, tracking: m.tracking,
    maxW: style === 'lower-third' ? maxW - LT_PAD : maxW,
    maxH: Math.round(room * (position === 'center' ? 0.55 : style === 'lower-third' ? 0.2 : 0.34)),
    maxChars: maxChars(format, style), maxLines: style === 'lower-third' ? 2 : display ? 3 : 3,
    ...extra,
  };
}

function textHtml(s, fmt, format, fonts, analysis) {
  if (!s.style) return { html: '', text: null };
  const list = words(s.source.text);
  const legible = legibility(analysis?.[s.id], s.style);
  const text = textSpec(s.style, s.position, fmt, format, fonts, { at: s.textAt, legible });
  const glow = s.natives.includes('glow') ? ' glow' : '';
  const mask = MASK_STYLES.has(s.style) ? ' mask' : '';
  const caret = s.style === 'typewriter' ? `<span id="CR-${s.id}" class="caret"></span>` : '';
  let body = `<div id="TB-${s.id}" class="tb${mask}">${wordsHtml(list, s.style)}${caret}</div>`;
  if (s.style === 'lower-third') {
    body = `<div class="lt"><div id="LP-${s.id}" class="lt-panel"></div><div id="LB-${s.id}" class="lt-bar"></div>${body}</div>`;
  }
  const plate = legible.mode === 'plate' ? `<div id="PL-${s.id}" class="plate" data-layout-allow-overflow></div>` : '';
  const scrimSide = s.style === 'lower-third' ? 'bottom' : s.position;
  const scrimAlpha = legible.mode === 'own' ? 0.3 : legible.mode === 'plate' ? 0.22 : legible.alpha;
  return {
    text,
    html: `<div id="SC-${s.id}" class="scrim scrim-${scrimSide}" style="--sa: ${scrimAlpha}"></div>`
      + `<div id="X-${s.id}" class="txt pos-${s.position} style-${s.style} face-${text.face.replace(/\s+/g, '-')}${glow} legible-${legible.mode}" `
      + `data-layout-allow-occlusion>${plate}${body}</div>`,
  };
}

/** Relative luminance (WCAG) of a #rrggbb colour, or null. */
function hexLum(hex) {
  const m = /^#?([0-9a-f]{6})$/i.exec(String(hex || '').trim());
  if (!m) return null;
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(m[1].slice(i, i + 2), 16) / 255)
    .map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/**
 * How the logo is shown: on a light plate when it is dark and the brand background is dark (a black wordmark
 * vanishes on the end card), and never scaled past 2× its pixels (a 149 px header logo goes soft at 600 px).
 * logo: {width, height, lum} from legibility.logoStats, or null when unknown.
 */
export function logoFit(logo, brand, warnings = []) {
  const bg = hexLum(brand.background) ?? 0.02;
  const plate = Boolean(logo && bg < 0.2 && logo.lum < 0.45);
  const scale = 2;
  if (logo && logo.width < 400) {
    warnings.push(`Loggan är bara ${logo.width}×${logo.height} px och visas högst ${scale}× så att den inte blir `
      + 'suddig. Ladda upp en större PNG (minst 1000 px bred) eller en SVG-export.');
  }
  return { plate, maxW: logo ? logo.width * scale : Infinity, maxH: logo ? logo.height * scale : Infinity };
}

/** <img> for the logo inside its box, capped by the box and by logoFit; on a plate when logoFit asks for one. */
function logoImg(logoName, boxW, boxH, look) {
  const w = Math.round(Math.min(boxW, look?.maxW ?? Infinity));
  const h = Math.round(Math.min(boxH, look?.maxH ?? Infinity));
  const img = `<img src="assets/${logoName}" alt="" style="max-width: ${w}px; max-height: ${h}px">`;
  return look?.plate ? `<div class="logo-plate">${img}</div>` : img;
}

function logoHtml(s, logoName, fmt, look) {
  const kind = s.natives.includes('logo-sting') ? 'sting' : s.natives.includes('logo-reveal') ? 'reveal' : null;
  if (!kind || !logoName) return '';
  const { W, H, safe } = fmt;
  const maxW = Math.round((W - safe.left - safe.right) * 0.6);
  // Above centered text, centered otherwise.
  const top = s.style && s.position === 'center' ? safe.top + 20 : Math.round(H * 0.36);
  return `<div id="LG-${s.id}" class="logo-fx logo-${kind}" style="top: ${top}px">`
    + `<div id="LR-${s.id}" class="logo-ring"></div>${logoImg(logoName, maxW, H * 0.12, look)}</div>`;
}

function sceneHtml(s, fmt, format, music, fonts, analysis, look, logoName, logoLook) {
  const n = s.natives;
  const grade = s.grade ? ` ${s.grade}` : look ? ' look' : '';
  const tint = s.grade && s.grade !== 'grade-noir' ? `<div class="tint tint-${s.grade.slice(6)}"></div>` : '';
  const vignette = n.includes('vignette') ? 'vignette' : look ? 'vignette vignette-lite' : '';
  const grain = n.includes('grain') ? 'grain' : look ? 'grain grain-lite' : '';
  const overlays = [
    tint,
    n.includes('dark-to-light') ? `<div id="BL-${s.id}" class="bloom" data-layout-allow-overflow></div>` : '',
    vignette ? `<div class="${vignette}"></div>` : '',
    n.includes('leak-overlay') ? `<div id="LO-${s.id}" class="leak-ov" data-layout-allow-overflow></div>` : '',
    n.includes('light-sweep') ? `<div id="SW-${s.id}" class="sweep-wrap" data-layout-allow-overflow><div class="sweep-band" data-layout-allow-overflow></div></div>` : '',
    grain ? `<div class="${grain}"><div id="GT-${s.id}" class="grain-tex" data-layout-allow-overflow></div></div>` : '',
    n.includes('beat-punch') ? `<div id="PF-${s.id}" class="punch-flash"></div>` : '',
  ].join('');
  const { html: textBlock, text } = textHtml(s, fmt, format, fonts, analysis);
  const t = s.transition;
  const extras = [
    t && t.type === 'wipe' ? `<div id="E-${s.id}" class="edge"></div>` : '',
    t && t.type === 'light-leak' ? `<div id="LK-${s.id}" class="tleak" data-layout-allow-overflow></div>` : '',
    t && t.type === 'glitch' ? `<div id="GB-${s.id}" class="gbars"></div>` : '',
  ].join('');
  const html = `
      <div id="L-${s.id}" class="layer" style="z-index: ${10 + s.idx}">
        <div id="T-${s.id}" class="tr">
          <div id="C-${s.id}" class="cam" data-layout-allow-overflow><div id="K-${s.id}" class="shk"><div id="F-${s.id}" class="fx"><div id="B-${s.id}" class="fx"><div id="G-${s.id}" class="fx${grade}">
            ${mediaHtml(s, music)}
          </div></div></div></div></div>
          ${overlays}
          ${logoHtml(s, logoName, fmt, logoLook)}
          ${textBlock}
        </div>
        ${extras}
      </div>`;
  return { html, text };
}

function endHtml(e, fmt, format, spec, brand, logoName, fonts, logoLook) {
  const { W, H, safe } = fmt;
  const maxW = W - safe.left - safe.right;
  const list = words(spec.cta.text);
  const host = String(spec.cta.url || '').replace(/^https?:\/\//, '').replace(/\/$/, '');
  const logo = logoName
    ? `<div id="ELW-${e.id}" class="end-logo">${logoImg(logoName, maxW * 0.7, H * 0.16, logoLook)}</div>`
    : `<div id="ELW-${e.id}" class="end-word">${esc(brand.name || '')}</div>`;
  e.text = textSpec('rise', 'center', fmt, format, fonts, { at: e.textAt + 0.25, maxH: Math.round((H - safe.top - safe.bottom) * 0.3), legible: { mode: 'own' } });
  return `
      <div id="L-${e.id}" class="layer end" style="z-index: ${10 + e.idx}">
        <div id="T-${e.id}" class="tr">
          <div id="EB-${e.id}" class="end-bg" data-layout-allow-overflow></div>
          <div class="grain grain-lite"><div id="GT-${e.id}" class="grain-tex" data-layout-allow-overflow></div></div>
          <div class="end-inner">
            ${logo}
            <div id="X-${e.id}" class="txt-end face-${e.text.face.replace(/\s+/g, '-')}"><div id="TB-${e.id}" class="tb mask">${wordsHtml(list, 'rise')}</div></div>
            ${host ? `<div id="EP-${e.id}" class="end-pill">${esc(host)}</div>` : ''}
          </div>
          <div id="SW-${e.id}" class="sweep-wrap" data-layout-allow-overflow><div class="sweep-band" data-layout-allow-overflow></div></div>
        </div>
      </div>`;
}

/**
 * Brand look as an SVG colour matrix: blacks lifted a touch toward the brand background, highlights warmed or cooled
 * toward the accent. Subtle by design – it unifies footage from different sources into one film.
 */
export function lookMatrix(brand) {
  const bg = rgb(hex(brand.background, DEFAULT_BRAND.background)).map((v) => v / 255);
  const ac = rgb(hex(brand.accent, DEFAULT_BRAND.accent)).map((v) => v / 255);
  const mean = (ac[0] + ac[1] + ac[2]) / 3;
  const lift = 0.04;
  const gains = ac.map((c) => 1 + 0.06 * (c - mean));
  const rows = [0, 1, 2].map((i) => {
    const row = [0, 0, 0, 0, r3(bg[i] * lift + 0.004)];
    row[i] = r3(gains[i] * (1 - lift));
    return row;
  });
  return [...rows.flat(), 0, 0, 0, 1, 0].join(' ');
}

function defsHtml(seq, brand, look) {
  const filters = [];
  if (look) filters.push(`<filter id="look" color-interpolation-filters="sRGB"><feColorMatrix type="matrix" values="${lookMatrix(brand)}"/></filter>`);
  seq.forEach((s, i) => {
    const t = s.transition;
    if (!t || !BLUR_TRANSITIONS[t.type] || !i) return;
    // Directional motion blur for fast moves: one filter for the incoming scene, one for the outgoing.
    for (const side of ['I', 'O']) {
      filters.push(`<filter id="MB${side}-${s.id}" x="-20%" y="-20%" width="140%" height="140%" color-interpolation-filters="sRGB">`
        + `<feGaussianBlur id="MB${side}G-${s.id}" stdDeviation="0 0"/></filter>`);
    }
  });
  if (!filters.length) return '';
  return `\n      <svg class="fx-defs" width="0" height="0" aria-hidden="true" data-layout-ignore><defs>${filters.join('')}</defs></svg>`;
}

function fontCss(fonts) {
  return fonts.map((f) => `
      @font-face { font-family: '${f.family}'; src: url("fonts/${f.file}") format('${f.file.endsWith('.ttf') ? 'truetype' : 'woff2'}'); font-weight: ${f.weight}; font-style: ${f.style}; font-display: block; }`).join('');
}

function css(fmt, brand, fonts, faces) {
  const { W, H, safe } = fmt;
  const bg = hex(brand.background, DEFAULT_BRAND.background);
  const fg = hex(brand.foreground, DEFAULT_BRAND.foreground);
  const accent = hex(brand.accent, DEFAULT_BRAND.accent);
  const paper = hex(brand.paper, DEFAULT_BRAND.paper);
  const ink = hex(brand.ink, DEFAULT_BRAND.ink);
  const contrast = (a, b) => { const [x, y] = [luminance(a), luminance(b)].sort((m, n) => n - m); return (x + 0.05) / (y + 0.05); };
  const emInk = contrast(ink, accent) >= contrast('#ffffff', accent) ? ink : '#ffffff';
  // Readable accent on dark footage: lift very dark brand accents.
  const accentText = luminance(accent) < 0.12 ? mix(accent, '#ffffff', 0.35) : accent;
  const deep = mix(bg, '#000000', 0.35);
  const ext = Array.from({ length: 10 }, (_, i) => mix(mix(accent, bg, 0.55), deep, i / 9));
  const extShadow = ext.map((c, i) => `calc(var(--d) * ${r3(0.12 * (i + 1))}px) calc(var(--d) * ${r3(0.14 * (i + 1))}px) 0 ${c}`).join(', ');
  const noise = "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")";
  const family = (key) => `'${FONT_FACES[key].css}', ${FONT_FACES[key].fallback}`;
  const displayCaps = faces.display === 'anton';
  return `${fontCss(fonts)}
      :root { --bg: ${bg}; --fg: ${fg}; --accent: ${accent}; --accent-text: ${accentText}; --paper: ${paper}; --ink: ${ink}; --em-ink: ${emInk};
        --font-text: ${family(faces.text)}; --font-display: ${family(faces.display)}; --plate: ${rgba(mix(bg, '#000000', 0.25), 0.8)}; }
      * { margin: 0; padding: 0; box-sizing: border-box; }
      html, body { width: ${W}px; height: ${H}px; overflow: hidden; background: var(--bg); }
      #root { position: relative; width: 100%; height: 100%; overflow: hidden; background: var(--bg); font-family: var(--font-text);
        font-kerning: normal; font-feature-settings: "kern" 1, "liga" 1, "calt" 1; text-rendering: optimizeLegibility; -webkit-font-smoothing: antialiased; }
      .fx-defs { position: absolute; width: 0; height: 0; overflow: hidden; }
      .layer { position: absolute; inset: 0; overflow: hidden; opacity: 0; }
      .tr { position: absolute; inset: 0; overflow: hidden; background: var(--bg); }
      .cam, .shk, .fx { position: absolute; inset: 0; transform-origin: 50% 50%; }
      .media { position: absolute; left: 0; top: 0; width: 100%; height: 100%; display: block; }
      .fit-cover { object-fit: cover; }
      .fit-contain { object-fit: contain; }
      .bgfill { object-fit: cover; filter: blur(48px) brightness(0.5) saturate(1.2); }
      .look { filter: url(#look) contrast(1.05) saturate(1.07); }
      .grade-warm { filter: sepia(0.16) saturate(1.12) contrast(1.06) brightness(1.02); }
      .grade-noir { filter: grayscale(1) contrast(1.28) brightness(0.96); }
      .grade-duotone { filter: grayscale(1) contrast(1.15) brightness(1.05); }
      .grade-cool, .grade-forest, .grade-tomato { filter: saturate(0.92) contrast(1.06); }
      .tint { position: absolute; inset: 0; pointer-events: none; }
      .tint-warm { background: linear-gradient(180deg, rgba(255, 170, 90, 0.16), rgba(120, 60, 20, 0.18)); mix-blend-mode: soft-light; }
      .tint-duotone { background: var(--accent); mix-blend-mode: color; opacity: 0.85; }
      .tint-cool { background: #1d3fbf; mix-blend-mode: soft-light; opacity: 0.45; }
      .tint-forest { background: #1f5a3a; mix-blend-mode: soft-light; opacity: 0.5; }
      .tint-tomato { background: #e2462c; mix-blend-mode: soft-light; opacity: 0.4; }
      .vignette { position: absolute; inset: 0; pointer-events: none; background: radial-gradient(ellipse 78% 70% at 50% 48%, transparent 50%, rgba(0, 0, 0, 0.62) 100%); }
      .vignette-lite { background: radial-gradient(ellipse 85% 78% at 50% 46%, transparent 58%, rgba(0, 0, 0, 0.34) 100%); }
      .grain { position: absolute; inset: 0; overflow: hidden; pointer-events: none; }
      .grain-tex { position: absolute; left: -25%; top: -25%; width: 150%; height: 150%; background: ${noise}; background-size: 300px 300px; opacity: 0.12; mix-blend-mode: overlay; }
      .grain-lite .grain-tex { opacity: 0.055; }
      .punch-flash { position: absolute; inset: 0; pointer-events: none; opacity: 0; background: #fff6e8; mix-blend-mode: screen; }
      .bloom { position: absolute; left: -30%; top: -10%; width: 160%; height: 120%; pointer-events: none; opacity: 0;
        background: radial-gradient(closest-side, ${rgba(mix(accent, '#ffffff', 0.55), 0.9)} 0%, ${rgba(accent, 0.35)} 45%, rgba(0, 0, 0, 0) 75%); mix-blend-mode: screen; }
      .leak-ov, .tleak { position: absolute; left: -20%; top: -10%; width: 140%; height: 120%; pointer-events: none; opacity: 0; mix-blend-mode: screen;
        background: radial-gradient(ellipse 45% 55% at 35% 42%, rgba(255, 236, 200, 0.95) 0%, rgba(255, 170, 80, 0.55) 35%, rgba(214, 120, 40, 0) 72%); filter: blur(18px); }
      .tleak { z-index: 5; }
      .sweep-wrap { position: absolute; inset: 0; pointer-events: none; overflow: hidden; }
      .sweep-band { position: absolute; top: -25%; left: 41%; width: 18%; height: 150%; transform: rotate(16deg);
        background: linear-gradient(90deg, rgba(255, 255, 255, 0), rgba(255, 255, 255, 0.32), rgba(255, 255, 255, 0)); mix-blend-mode: screen; }
      .edge { position: absolute; left: 0; top: 0; width: 24px; height: 100%; background: var(--accent); box-shadow: 0 0 48px var(--accent); z-index: 6; }
      .gbars { position: absolute; left: 0; top: 0; width: 100%; height: 9%; opacity: 0; z-index: 6; mix-blend-mode: difference;
        background: linear-gradient(90deg, rgba(255, 0, 90, 0.75), rgba(0, 255, 230, 0.75)); }
      #flash { position: absolute; inset: 0; background: #fff8ec; opacity: 0; z-index: 900; pointer-events: none; }
      .logo-fx { position: absolute; left: 0; right: 0; display: flex; justify-content: center; align-items: center; opacity: 0; pointer-events: none; }
      .logo-fx img { display: block; object-fit: contain; filter: drop-shadow(0 8px 28px rgba(0, 0, 0, 0.45)); }
      .logo-ring { position: absolute; left: 50%; top: 50%; width: 360px; height: 360px; margin: -180px 0 0 -180px; border-radius: 50%;
        border: 10px solid var(--accent); opacity: 0; }
      .scrim { position: absolute; inset: 0; pointer-events: none; opacity: 0; --sa: 0.42; }
      .scrim-bottom { background: linear-gradient(0deg, rgba(0, 0, 0, var(--sa)) 0%, rgba(0, 0, 0, var(--sa)) 20%,
        rgba(0, 0, 0, calc(var(--sa) * 0.9)) 38%, rgba(0, 0, 0, calc(var(--sa) * 0.45)) 52%, rgba(0, 0, 0, 0) 68%); }
      .scrim-top { background: linear-gradient(180deg, rgba(0, 0, 0, var(--sa)) 0%, rgba(0, 0, 0, var(--sa)) 20%,
        rgba(0, 0, 0, calc(var(--sa) * 0.9)) 38%, rgba(0, 0, 0, calc(var(--sa) * 0.45)) 52%, rgba(0, 0, 0, 0) 68%); }
      .scrim-center { background: radial-gradient(ellipse 95% 34% at 50% 48%, rgba(0, 0, 0, var(--sa)) 0%, rgba(0, 0, 0, calc(var(--sa) * 0.8)) 45%,
        rgba(0, 0, 0, calc(var(--sa) * 0.3)) 75%, rgba(0, 0, 0, 0) 100%); }
      .plate { position: absolute; left: 0; top: 0; width: 0; height: 0; background: var(--plate); border-radius: 22px;
        box-shadow: 0 18px 60px rgba(0, 0, 0, 0.35); opacity: 0; }
      .txt { position: absolute; left: ${safe.left}px; right: ${safe.right}px; display: flex; justify-content: center; pointer-events: none; }
      .pos-top { top: ${safe.top}px; }
      .pos-center { top: ${safe.top}px; bottom: ${safe.bottom}px; align-items: center; }
      .pos-bottom { bottom: ${safe.bottom}px; }
      .tb { position: relative; width: 100%; text-align: center; color: var(--fg); font-family: var(--font-text); font-weight: 700; line-height: 1.06;
        letter-spacing: -0.02em; text-shadow: 0 2px 6px rgba(0, 0, 0, 0.28), 0 10px 34px rgba(0, 0, 0, 0.38); }
      .face-playfair-display .tb { font-weight: 600; }
      .face-playfair-display .tb .em .wi { font-style: italic; font-weight: 500; }
      .legible-shadow .tb { text-shadow: 0 2px 8px rgba(0, 0, 0, 0.4), 0 12px 40px rgba(0, 0, 0, 0.45); }
      .legible-plate .tb { text-shadow: none; }
      .tb .w { display: inline-block; vertical-align: top; }
      .tb.mask .w { overflow: hidden; padding: 0.16em 0.05em 0.1em; margin: -0.16em 0 -0.1em; }
      .tb .wi { display: inline-block; }
      .tb .em .wi { color: var(--accent-text); }
      .tb .ch { display: inline-block; }
      .style-slam .tb, .style-extrusion .tb, .style-caption .tb, .style-chunk .tb { font-family: var(--font-display); font-weight: ${displayCaps ? 400 : 700};
        ${displayCaps ? 'text-transform: uppercase; ' : ''}line-height: 0.98; letter-spacing: ${displayCaps ? '0.01em' : '-0.02em'}; }
      .style-chunk .tb { font-family: var(--font-text); font-weight: 700; text-transform: none; letter-spacing: -0.04em; line-height: 1.02;
        display: grid; place-items: center; }
      .style-chunk .ck { grid-area: 1 / 1; display: block; }
      .style-slam .tb { color: var(--paper); text-shadow: 0 0.035em 0 rgba(0, 0, 0, 0.35), 0 12px 44px rgba(0, 0, 0, 0.55); }
      .style-extrusion .tb { color: var(--paper); text-shadow: none; }
      .style-extrusion .w { --d: 22; text-shadow: ${extShadow}, calc(var(--d) * 1.6px) calc(var(--d) * 2.2px) calc(var(--d) * 1.6px) rgba(0, 0, 0, 0.5); }
      .style-caption .tb { display: grid; place-items: center; }
      .style-caption .w { grid-area: 1 / 1; }
      .style-typewriter .tb { font-weight: 600; }
      .caret { display: inline-block; width: 0.09em; height: 0.92em; margin-left: 0.06em; vertical-align: -0.1em; background: var(--accent); }
      .style-highlight .w { position: relative; }
      .style-highlight .w .wi { position: relative; z-index: 1; }
      .style-highlight .em .wi { color: var(--em-ink); }
      .style-highlight .mk { position: absolute; left: 0; right: 0; top: 0.12em; bottom: 0.04em; background: var(--accent); transform-origin: 0 50%; z-index: 0; }
      .style-shimmer .wi { background: linear-gradient(100deg, var(--fg) 0%, var(--fg) 38%, var(--accent-text) 50%, var(--fg) 62%, var(--fg) 100%);
        background-size: 260% 100%; background-position: 100% 0; -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
      .glow .tb { text-shadow: 0 0 18px var(--accent), 0 0 46px var(--accent); }
      .style-lower-third { justify-content: flex-start; }
      .lt { position: relative; padding: 26px 40px 30px 52px; max-width: 100%; }
      .lt-panel { position: absolute; inset: 0; background: ${rgba(bg, 0.86)}; border-radius: 6px; }
      .lt-bar { position: absolute; left: 0; top: 0; bottom: 0; width: 12px; background: var(--accent); transform-origin: 50% 100%; border-radius: 6px 0 0 6px; }
      .lt .tb { position: relative; text-align: left; width: auto; text-shadow: none; font-weight: 600; }
      .end-bg { position: absolute; inset: -6%; background: radial-gradient(ellipse 70% 46% at 50% 40%, ${rgba(accent, 0.38)} 0%, ${rgba(accent, 0)} 72%),
        linear-gradient(180deg, ${mix(bg, '#ffffff', 0.06)} 0%, ${bg} 60%, ${deep} 100%); }
      .end-inner { position: absolute; left: ${safe.left}px; right: ${safe.right}px; top: ${safe.top}px; bottom: ${safe.bottom}px;
        display: flex; flex-direction: column; align-items: center; justify-content: center; gap: ${Math.round(Math.min(W, H) * 0.055)}px; }
      .end-logo { display: flex; justify-content: center; }
      .end-logo img { display: block; object-fit: contain; }
      .logo-plate { display: inline-flex; padding: 22px 30px; border-radius: 22px; background: #ffffff;
        box-shadow: 0 18px 50px rgba(0, 0, 0, 0.35); }
      .logo-plate img { display: block; object-fit: contain; }
      .end-word { font-family: var(--font-text); font-weight: 700; font-size: 72px; letter-spacing: 0.06em; text-transform: uppercase; color: var(--fg); }
      .txt-end { width: 100%; display: flex; justify-content: center; }
      .txt-end .tb { text-shadow: none; }
      .end-pill { font-family: var(--font-text); font-weight: 600; font-size: ${Math.round(Math.min(W, H) * 0.04)}px; letter-spacing: -0.005em; color: var(--em-ink); background: var(--accent);
        padding: 0.42em 1.05em; border-radius: 999px; box-shadow: 0 14px 40px ${rgba(accent, 0.35)}; }`;
}

/** SFX cue sheet: transition accents, slam impacts, explicit catalog sounds, a riser into the outro. */
export function planSfx(seq, total, { outro = false, auto = true } = {}) {
  const cues = [];
  const has = (t, kinds) => cues.some((c) => Math.abs(c.t - t) < 0.12 && kinds.includes(c.kind));
  for (const s of seq) {
    if (s.isEnd) continue;
    for (const native of s.natives || []) {
      const kind = sfxOf(native);
      if (!kind) continue;
      if (['riser', 'swell'].includes(kind)) cues.push({ kind, t: r3(s.end), src: s.id });
      else if (kind === 'tapestop') cues.push({ kind, t: r3(Math.max(s.start, s.end - 0.6)), at: 'start', src: s.id });
      else if (kind === 'room-tone') cues.push({ kind, t: r3(s.winStart), at: 'start', dur: r3(s.winEnd - s.winStart), src: s.id });
      else if (['whoosh', 'swish', 'impact', 'boom'].includes(kind)) cues.push({ kind, t: r3(s.idx ? s.start : s.textAt), src: s.id });
      else cues.push({ kind, t: r3(s.textAt), src: s.id });
    }
  }
  if (auto) {
    for (const s of seq) {
      const tr = s.transition;
      const sound = tr && TRANSITION_SFX[tr.type];
      if (sound && !has(s.start, ['whoosh', 'swish', 'impact', 'boom'])) cues.push({ ...sound, t: r3(s.start), src: s.id, auto: true });
      if (!s.isEnd && ['slam', 'extrusion'].includes(s.style) && s.idx === 0 && !has(s.textAt, ['impact', 'boom'])) {
        cues.push({ kind: 'impact', t: r3(s.textAt), gainDb: -18, src: s.id, auto: true });
      }
      if ((s.natives || []).includes('logo-sting') && !has(s.textAt, ['impact'])) cues.push({ kind: 'impact', t: r3(s.textAt + 0.28), src: s.id, auto: true });
      if ((s.natives || []).includes('logo-reveal')) cues.push({ kind: 'shimmer', t: r3(s.textAt + 0.4), src: s.id, auto: true });
    }
    if (outro && total > 2) cues.push({ kind: 'riser', t: r3(total), dur: 1.4, gainDb: -18, src: 'outro', auto: true });
  }
  return cues.filter((c) => c.t >= 0 && c.t <= total + 0.05).sort((a, b) => a.t - b.t);
}

/**
 * Build the project.
 * files: {assetId: {path, kind, hasAudio, duration}} for every scene asset (and optionally the logo).
 * beats: beat grid (beats.js) to snap to; analysis: {sceneId: luminance stats} (legibility.js); outro: a brand outro
 * follows the cut (adds a riser). Returns {dir, total, warnings, config, timing, sfx, intent}.
 */
export function compose({ spec, brand = {}, files, outDir, logoId = null, logo = null, beats = null, analysis = null, outro = false, autoSfx = true }) {
  const warnings = [];
  const format = FORMATS[spec.format] ? spec.format : '9:16';
  const fmt = FORMATS[format];
  const prepared = {};
  mkdirSync(join(outDir, 'assets'), { recursive: true });
  mkdirSync(join(outDir, 'fonts'), { recursive: true });
  for (const [id, file] of Object.entries(files)) {
    const name = `${id}${extname(file.path).toLowerCase() || (file.kind === 'video' ? '.mp4' : '.jpg')}`;
    copyFileSync(file.path, join(outDir, 'assets', name));
    prepared[id] = { ...file, name };
  }
  const brandFonts = resolveBrandFonts(brand.font_family, { display: brand.display_font });
  if (brandFonts.warning) warnings.push(brandFonts.warning);
  const faces = { text: brandFonts.text, display: brandFonts.display };
  const fonts = fontFiles(['inter', faces.text, faces.display]);
  for (const f of fonts) copyFileSync(join(FONTS_DIR, f.file), join(outDir, 'fonts', f.file));
  const music = Boolean(spec.music_asset_id);
  const logoName = logoId && prepared[logoId] ? prepared[logoId].name : null;
  const { scenes, endcard, total, timing } = plan(spec, prepared, warnings, { grid: music ? beats : null, logo: Boolean(logoName) });
  const look = brand.look !== 'none';
  const logoLook = logoName ? logoFit(logo, brand, warnings) : null;
  const parts = scenes.map((s) => sceneHtml(s, fmt, format, music, faces, analysis, look, logoName, logoLook));
  const endPart = endcard ? endHtml(endcard, fmt, format, spec, brand, logoName, faces, logoLook) : '';
  const seq = endcard ? [...scenes, endcard] : scenes;
  const grid = music ? beats : null;
  const sfx = planSfx(seq, total, { outro, auto: autoSfx && brand.sfx !== false });
  const config = {
    W: fmt.W, H: fmt.H, total, format, zones: PLATFORM_ZONES[format], read: { cps: READ.cps, minEvent: READ.minEvent },
    beats: grid ? { period: grid.period, times: grid.beats.filter((b) => b.t <= total + 0.01).map((b) => [b.t, b.down ? 1 : 0]) } : null,
    scenes: scenes.map((s, i) => ({
      id: s.id, idx: s.idx, start: s.start, end: s.end, winStart: s.winStart, winEnd: s.winEnd, textAt: s.textAt,
      transition: s.transition, effects: s.natives, camera: s.camera, text: parts[i].text, kind: s.kind,
    })),
    endcard: endcard && {
      id: endcard.id, idx: endcard.idx, isEnd: true, start: endcard.start, end: endcard.end, textAt: endcard.textAt,
      winStart: endcard.winStart, winEnd: endcard.winEnd, transition: endcard.transition, text: endcard.text,
    },
  };
  const runtime = `const GLUE_WORDS = ${JSON.stringify(GLUE_WORDS)};\nconst breakLines = ${breakLines.toString()};\n${RUNTIME}`;
  const html = `<!doctype html>
<html lang="sv">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=${fmt.W}, height=${fmt.H}">
    <title>${esc(spec.title)}</title>
    <script src="${GSAP_URL}"></script>
    <style>${css(fmt, brand, fonts, faces)}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="${total}" data-width="${fmt.W}" data-height="${fmt.H}" data-fps="${spec.fps || 30}">${defsHtml(seq, brand, look)}${parts.map((p) => p.html).join('')}${endPart}
      <div id="flash"></div>
    </div>
    <script type="application/json" id="cut-config">${JSON.stringify(config).replace(/</g, '\\u003c')}</script>
    <script>
${runtime}
    </script>
  </body>
</html>
`;
  writeFileSync(join(outDir, 'index.html'), html);
  writeFileSync(join(outDir, 'meta.json'), JSON.stringify({ id: 'cut', name: 'cut', createdAt: '2026-10-09T00:00:00.000Z' }, null, 2));
  // What QA should not flag: the intentional black open of dark-to-light.
  const intent = {
    dark: scenes.filter((s) => s.natives.includes('dark-to-light')).map((s) => ({ start: s.winStart, end: r3(s.start + Math.min((s.end - s.start) * 0.75, 3.2) * 0.6) })),
  };
  return { dir: outDir, total, warnings, config, timing, sfx, intent, fonts: faces };
}
