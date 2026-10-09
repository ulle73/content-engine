// Build a HyperFrames project (index.html + assets + fonts) from a cut spec (cut/v1) with the generic cut template.
import { copyFileSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, extname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { resolve, transitionDuration } from './support.js';

const HERE = dirname(fileURLToPath(import.meta.url));
const FONTS = join(HERE, '..', 'template', 'fonts');
const RUNTIME = readFileSync(join(HERE, 'runtime.js'), 'utf8');
export const GSAP_URL = 'https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js';

export const FORMATS = {
  '9:16': { W: 1080, H: 1920, safe: { top: 250, bottom: 430, left: 110, right: 110 } },
  '4:5': { W: 1080, H: 1350, safe: { top: 110, bottom: 150, left: 90, right: 90 } },
  '1:1': { W: 1080, H: 1080, safe: { top: 80, bottom: 90, left: 80, right: 80 } },
  '16:9': { W: 1920, H: 1080, safe: { top: 80, bottom: 100, left: 140, right: 140 } },
};
const HARD_SWAPS = new Set(['cut', 'flash', 'glitch']);
const CAMERAS = ['ken-burns', 'push-in', 'pull-back'];
const CHAR_STYLES = new Set(['typewriter', 'cascade', 'scramble', 'tracking-in']);
const MASK_STYLES = new Set(['rise', 'line-reveal', 'highlight', 'shimmer', 'lower-third']);
const LT_PAD = 92; // .lt horizontal padding (40 + 52)
const BASE_SIZE = {
  slam: [176, 132], extrusion: [170, 128], caption: [158, 128], rise: [108, 86], 'line-reveal': [104, 84],
  'blur-in': [104, 84], typewriter: [80, 68], 'tracking-in': [96, 80], cascade: [104, 84], highlight: [100, 84],
  shimmer: [108, 86], 'lower-third': [66, 66], scramble: [96, 80],
};
const DEFAULT_BRAND = { background: '#111814', foreground: '#ffffff', accent: '#68766f', muted: '#dfe7e3', paper: '#f6f8f7', ink: '#111814' };

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const r3 = (n) => Math.round(n * 1000) / 1000;
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

function wordsHtml(list, style) {
  const mark = style === 'highlight' && !list.some((w) => w.em) && list.length ? list.length - 1 : -1;
  return list.map((w, i) => {
    const inner = CHAR_STYLES.has(style)
      ? [...w.text].map((ch) => `<span class="ch">${esc(ch)}</span>`).join('')
      : esc(w.text);
    const em = w.em || i === mark;
    const marker = style === 'highlight' && em ? '<span class="mk"></span>' : '';
    return `<span class="w${em ? ' em' : ''}" data-layout-allow-overflow>${marker}<span class="wi">${inner}</span></span>`;
  }).join(' ');
}

function plan(spec, files, warnings) {
  const scenes = [];
  let clock = 0;
  spec.scenes.forEach((s, idx) => {
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
    const file = files[s.asset_id];
    if (!file) throw new Error(`Mediefil saknas för ${where}`);
    const camera = cams[0] || (file.kind === 'image' ? 'ken-burns' : 'micro-push');
    let style = null;
    if (s.text) {
      style = resolve('text', s.text_style);
      if (s.text_style && !style) warnings.push(`${where}: textstilen ${s.text_style} stöds inte av klippmallen; standardstilen används.`);
      style = style || (s.purpose === 'hook' ? 'slam' : 'rise');
    }
    const duration = Number(s.duration_s);
    scenes.push({
      id: s.id, idx, start: r3(clock), end: r3(clock + duration), transition, natives, camera,
      grade: grades[0] || null, style, kind: file.kind, file, source: s,
      position: style === 'lower-third' ? 'bottom' : s.text_position || (s.purpose === 'hook' || s.purpose === 'cta' ? 'center' : 'bottom'),
    });
    clock += duration;
  });
  // Clamp each transition to what the two neighbouring scenes can carry.
  scenes.forEach((s, i) => {
    if (!s.transition || s.transition.cut || !i) return;
    const room = Math.min(s.end - s.start, scenes[i - 1].end - scenes[i - 1].start) * 0.6;
    s.transition.d = r3(Math.min(s.transition.d, room));
  });
  let endcard = null;
  if (spec.cta) {
    const duration = Number(spec.cta.duration_s || 2.5);
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
  });
  if (scenes.length) scenes[scenes.length - 1].winEnd = endcard ? scenes[scenes.length - 1].winEnd : total;
  return { scenes, endcard, total };
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

function textHtml(s, fmt) {
  if (!s.style) return { html: '', text: null };
  const { W, H, safe } = fmt;
  const list = words(s.source.text);
  const maxW = W - safe.left - safe.right;
  const room = H - safe.top - safe.bottom;
  const [center, side] = BASE_SIZE[s.style] || BASE_SIZE.rise;
  const text = {
    style: s.style,
    base: s.position === 'center' ? center : side,
    maxW: s.style === 'lower-third' ? maxW - LT_PAD : maxW,
    maxH: Math.round(room * (s.position === 'center' ? 0.55 : s.style === 'lower-third' ? 0.2 : 0.34)),
  };
  const glow = s.natives.includes('glow') ? ' glow' : '';
  const mask = MASK_STYLES.has(s.style) ? ' mask' : '';
  const caret = s.style === 'typewriter' ? `<span id="CR-${s.id}" class="caret"></span>` : '';
  let body = `<div id="TB-${s.id}" class="tb${mask}">${wordsHtml(list, s.style)}${caret}</div>`;
  if (s.style === 'lower-third') {
    body = `<div class="lt"><div id="LP-${s.id}" class="lt-panel"></div><div id="LB-${s.id}" class="lt-bar"></div>${body}</div>`;
  }
  const scrimSide = s.style === 'lower-third' ? 'bottom' : s.position;
  return {
    text,
    html: `<div id="SC-${s.id}" class="scrim scrim-${scrimSide}"></div>`
      + `<div id="X-${s.id}" class="txt pos-${s.position} style-${s.style}${glow}" data-layout-allow-occlusion>${body}</div>`,
  };
}

function sceneHtml(s, fmt, music) {
  const n = s.natives;
  const grade = s.grade ? ` ${s.grade}` : '';
  const tint = s.grade && s.grade !== 'grade-noir' ? `<div class="tint tint-${s.grade.slice(6)}"></div>` : '';
  const overlays = [
    tint,
    n.includes('dark-to-light') ? `<div id="BL-${s.id}" class="bloom" data-layout-allow-overflow></div>` : '',
    n.includes('vignette') ? '<div class="vignette"></div>' : '',
    n.includes('leak-overlay') ? `<div id="LO-${s.id}" class="leak-ov" data-layout-allow-overflow></div>` : '',
    n.includes('light-sweep') ? `<div id="SW-${s.id}" class="sweep-wrap" data-layout-allow-overflow><div class="sweep-band" data-layout-allow-overflow></div></div>` : '',
    n.includes('grain') ? `<div class="grain"><div id="GT-${s.id}" class="grain-tex" data-layout-allow-overflow></div></div>` : '',
  ].join('');
  const { html: textBlock, text } = textHtml(s, fmt);
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
          ${textBlock}
        </div>
        ${extras}
      </div>`;
  return { html, text };
}

function endHtml(e, fmt, spec, brand, logoName) {
  const { W, H, safe } = fmt;
  const maxW = W - safe.left - safe.right;
  const list = words(spec.cta.text);
  const host = String(spec.cta.url || '').replace(/^https?:\/\//, '').replace(/\/$/, '');
  const logo = logoName
    ? `<div id="ELW-${e.id}" class="end-logo"><img src="assets/${logoName}" alt="" style="max-width: ${Math.round(maxW * 0.62)}px; max-height: ${Math.round(H * 0.15)}px"></div>`
    : `<div id="ELW-${e.id}" class="end-word">${esc(brand.name || '')}</div>`;
  e.text = { style: 'rise', base: 104, maxW, maxH: Math.round((H - safe.top - safe.bottom) * 0.3) };
  return `
      <div id="L-${e.id}" class="layer end" style="z-index: ${10 + e.idx}">
        <div id="T-${e.id}" class="tr">
          <div id="EB-${e.id}" class="end-bg" data-layout-allow-overflow></div>
          <div class="grain"><div id="GT-${e.id}" class="grain-tex" data-layout-allow-overflow></div></div>
          <div class="end-inner">
            ${logo}
            <div id="X-${e.id}" class="txt-end"><div id="TB-${e.id}" class="tb mask">${wordsHtml(list, 'rise')}</div></div>
            ${host ? `<div id="EP-${e.id}" class="end-pill">${esc(host)}</div>` : ''}
          </div>
          <div id="SW-${e.id}" class="sweep-wrap" data-layout-allow-overflow><div class="sweep-band" data-layout-allow-overflow></div></div>
        </div>
      </div>`;
}

function css(fmt, brand) {
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
  return `
      @font-face { font-family: 'Inter'; src: url("fonts/inter-500.woff2") format('woff2'); font-weight: 500; font-display: block; }
      @font-face { font-family: 'Inter'; src: url("fonts/inter-600.woff2") format('woff2'); font-weight: 600; font-display: block; }
      @font-face { font-family: 'Inter'; src: url("fonts/inter-700.woff2") format('woff2'); font-weight: 700; font-display: block; }
      @font-face { font-family: 'Anton'; src: url("fonts/anton.woff2") format('woff2'); font-weight: 400; font-display: block; }
      :root { --bg: ${bg}; --fg: ${fg}; --accent: ${accent}; --accent-text: ${accentText}; --paper: ${paper}; --ink: ${ink}; --em-ink: ${emInk}; }
      * { margin: 0; padding: 0; box-sizing: border-box; }
      html, body { width: ${W}px; height: ${H}px; overflow: hidden; background: var(--bg); }
      #root { position: relative; width: 100%; height: 100%; overflow: hidden; background: var(--bg); font-family: 'Inter', sans-serif; }
      .layer { position: absolute; inset: 0; overflow: hidden; opacity: 0; }
      .tr { position: absolute; inset: 0; overflow: hidden; background: var(--bg); }
      .cam, .shk, .fx { position: absolute; inset: 0; transform-origin: 50% 50%; }
      .media { position: absolute; left: 0; top: 0; width: 100%; height: 100%; display: block; }
      .fit-cover { object-fit: cover; }
      .fit-contain { object-fit: contain; }
      .bgfill { object-fit: cover; filter: blur(48px) brightness(0.5) saturate(1.2); }
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
      .grain { position: absolute; inset: 0; overflow: hidden; pointer-events: none; }
      .grain-tex { position: absolute; left: -25%; top: -25%; width: 150%; height: 150%; background: ${noise}; background-size: 300px 300px; opacity: 0.12; mix-blend-mode: overlay; }
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
      .scrim { position: absolute; inset: 0; pointer-events: none; opacity: 0; }
      .scrim-bottom { background: linear-gradient(0deg, rgba(0, 0, 0, 0.74) 0%, rgba(0, 0, 0, 0.38) 30%, rgba(0, 0, 0, 0) 55%); }
      .scrim-top { background: linear-gradient(180deg, rgba(0, 0, 0, 0.72) 0%, rgba(0, 0, 0, 0.36) 30%, rgba(0, 0, 0, 0) 55%); }
      .scrim-center { background: radial-gradient(ellipse 95% 42% at 50% 47%, rgba(0, 0, 0, 0.5) 0%, rgba(0, 0, 0, 0.22) 55%, rgba(0, 0, 0, 0) 80%); }
      .txt { position: absolute; left: ${safe.left}px; right: ${safe.right}px; display: flex; justify-content: center; pointer-events: none; }
      .pos-top { top: ${safe.top}px; }
      .pos-center { top: ${safe.top}px; bottom: ${safe.bottom}px; align-items: center; }
      .pos-bottom { bottom: ${safe.bottom}px; }
      .tb { width: 100%; text-align: center; color: var(--fg); font-family: 'Inter', sans-serif; font-weight: 700; line-height: 1.04;
        letter-spacing: -0.015em; text-shadow: 0 6px 28px rgba(0, 0, 0, 0.45); }
      .tb .w { display: inline-block; vertical-align: top; }
      .tb.mask .w { overflow: hidden; padding: 0.16em 0.05em 0.1em; margin: -0.16em 0 -0.1em; }
      .tb .wi { display: inline-block; }
      .tb .em .wi { color: var(--accent-text); }
      .tb .ch { display: inline-block; }
      .style-slam .tb, .style-extrusion .tb, .style-caption .tb { font-family: 'Anton', sans-serif; font-weight: 400; text-transform: uppercase;
        line-height: 0.95; letter-spacing: 0.005em; }
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
      .lt-panel { position: absolute; inset: 0; background: ${rgba(bg, 0.84)}; }
      .lt-bar { position: absolute; left: 0; top: 0; bottom: 0; width: 12px; background: var(--accent); transform-origin: 50% 100%; }
      .lt .tb { position: relative; text-align: left; width: auto; text-shadow: none; }
      .end-bg { position: absolute; inset: -6%; background: radial-gradient(ellipse 70% 46% at 50% 40%, ${rgba(accent, 0.38)} 0%, ${rgba(accent, 0)} 72%),
        linear-gradient(180deg, ${mix(bg, '#ffffff', 0.06)} 0%, ${bg} 60%, ${deep} 100%); }
      .end-inner { position: absolute; left: ${safe.left}px; right: ${safe.right}px; top: ${safe.top}px; bottom: ${safe.bottom}px;
        display: flex; flex-direction: column; align-items: center; justify-content: center; gap: ${Math.round(Math.min(W, H) * 0.05)}px; }
      .end-logo { display: flex; justify-content: center; }
      .end-logo img { display: block; object-fit: contain; }
      .end-word { font-family: 'Inter', sans-serif; font-weight: 700; font-size: 72px; letter-spacing: 0.06em; text-transform: uppercase; color: var(--fg); }
      .txt-end { width: 100%; display: flex; justify-content: center; }
      .txt-end .tb { text-shadow: none; }
      .end-pill { font-family: 'Inter', sans-serif; font-weight: 600; font-size: 44px; color: var(--em-ink); background: var(--accent);
        padding: 18px 44px; border-radius: 999px; }`;
}

/**
 * Build the project.
 * files: {assetId: {path, kind, hasAudio, duration}} for every scene asset (and optionally the logo).
 * Returns {dir, total, warnings, config}.
 */
export function compose({ spec, brand = {}, files, outDir, logoId = null }) {
  const warnings = [];
  const fmt = FORMATS[spec.format] || FORMATS['9:16'];
  const prepared = {};
  mkdirSync(join(outDir, 'assets'), { recursive: true });
  mkdirSync(join(outDir, 'fonts'), { recursive: true });
  for (const [id, file] of Object.entries(files)) {
    const name = `${id}${extname(file.path).toLowerCase() || (file.kind === 'video' ? '.mp4' : '.jpg')}`;
    copyFileSync(file.path, join(outDir, 'assets', name));
    prepared[id] = { ...file, name };
  }
  for (const font of ['inter-500', 'inter-600', 'inter-700', 'anton']) {
    copyFileSync(join(FONTS, `${font}.woff2`), join(outDir, 'fonts', `${font}.woff2`));
  }
  const family = String(brand.font_family || '');
  if (family && !/inter/i.test(family)) {
    warnings.push(`Typsnittet ${family.split(',')[0]} finns inte i renderaren; Inter används.`);
  }
  const music = Boolean(spec.music_asset_id);
  const { scenes, endcard, total } = plan(spec, prepared, warnings);
  const parts = scenes.map((s) => sceneHtml(s, fmt, music));
  const endPart = endcard ? endHtml(endcard, fmt, spec, brand, logoId && prepared[logoId] ? prepared[logoId].name : null) : '';
  const config = {
    W: fmt.W, H: fmt.H, total,
    scenes: scenes.map((s, i) => ({
      id: s.id, idx: s.idx, start: s.start, end: s.end, winStart: s.winStart, winEnd: s.winEnd,
      transition: s.transition, effects: s.natives, camera: s.camera, text: parts[i].text,
    })),
    endcard: endcard && {
      id: endcard.id, idx: endcard.idx, isEnd: true, start: endcard.start, end: endcard.end,
      winStart: endcard.winStart, winEnd: endcard.winEnd, transition: endcard.transition, text: endcard.text,
    },
  };
  const html = `<!doctype html>
<html lang="sv">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=${fmt.W}, height=${fmt.H}">
    <title>${esc(spec.title)}</title>
    <script src="${GSAP_URL}"></script>
    <style>${css(fmt, brand)}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="${total}" data-width="${fmt.W}" data-height="${fmt.H}" data-fps="${spec.fps || 30}">${parts.map((p) => p.html).join('')}${endPart}
      <div id="flash"></div>
    </div>
    <script type="application/json" id="cut-config">${JSON.stringify(config).replace(/</g, '\\u003c')}</script>
    <script>
${RUNTIME}
    </script>
  </body>
</html>
`;
  writeFileSync(join(outDir, 'index.html'), html);
  writeFileSync(join(outDir, 'meta.json'), JSON.stringify({ id: 'cut', name: 'cut', createdAt: '2026-10-09T00:00:00.000Z' }, null, 2));
  return { dir: outDir, total, warnings, config };
}
