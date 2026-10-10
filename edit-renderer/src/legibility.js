// Legibility: sample the picture where the text will sit and choose how much help the text needs (soft shadow,
// a scrim of computed strength, or a solid plate) so white type reaches WCAG contrast on any footage.
import { spawn } from 'node:child_process';

const toLinear = (v) => (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4);
const toGamma = (L) => (L <= 0.0031308 ? L * 12.92 : 1.055 * L ** (1 / 2.4) - 0.055);
const ratio = (La, Lb) => (Math.max(La, Lb) + 0.05) / (Math.min(La, Lb) + 0.05);

/** The text band (canvas px) for a position, matching compose.js' layout. */
export function textBand(fmt, position, maxH) {
  const { W, H, safe } = fmt;
  const x0 = safe.left, x1 = W - safe.right;
  if (position === 'top') return { x0, x1, y0: safe.top, y1: safe.top + maxH * 0.7 };
  if (position === 'center') {
    const mid = safe.top + (H - safe.top - safe.bottom) / 2;
    return { x0, x1, y0: mid - maxH * 0.35, y1: mid + maxH * 0.35 };
  }
  return { x0, x1, y0: H - safe.bottom - maxH * 0.7, y1: H - safe.bottom };
}

/** Pixel stats (0..1 gamma-encoded luma) of a gray8 frame region. */
export function regionStats(gray, width, height, band, scale) {
  const vals = [];
  const y0 = Math.max(0, Math.floor(band.y0 / scale)), y1 = Math.min(height, Math.ceil(band.y1 / scale));
  const x0 = Math.max(0, Math.floor(band.x0 / scale)), x1 = Math.min(width, Math.ceil(band.x1 / scale));
  for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) vals.push(gray[y * width + x] / 255);
  if (!vals.length) return null;
  vals.sort((a, b) => a - b);
  const mean = vals.reduce((s, v) => s + v, 0) / vals.length;
  const std = Math.sqrt(vals.reduce((s, v) => s + (v - mean) ** 2, 0) / vals.length);
  const q = (p) => vals[Math.min(vals.length - 1, Math.floor(p * vals.length))];
  return { mean, std, p90: q(0.9), p95: q(0.95) };
}

/**
 * stats → treatment for white text. A black overlay of alpha a darkens a pixel v to v(1-a); find the smallest a with
 * 4.5:1 against the region's mean and 3:1 (large text) against its bright spots (p95). Busy regions get extra help.
 * Returns {mode: 'shadow' | 'scrim' | 'plate', alpha, contrast (estimated, after treatment), measured}.
 */
export function legibility(stats, style) {
  if (style === 'lower-third') return { mode: 'own', alpha: 0, contrast: null, measured: Boolean(stats) };
  if (!stats) return { mode: 'scrim', alpha: 0.42, contrast: null, measured: false };
  const need = (v, target) => {
    const vmax = toGamma(1.05 / target - 0.05);
    return v <= vmax ? 0 : 1 - vmax / v;
  };
  let a = Math.max(need(stats.mean, 4.5), need(stats.p95, 3));
  if (stats.std > 0.2) a = Math.max(a, 0.38);
  a = Math.min(0.92, a);
  let mode, alpha;
  if (a < 0.14) { mode = 'shadow'; alpha = 0.18; }
  else if (a <= 0.45) { mode = 'scrim'; alpha = Math.min(0.62, a + 0.08); }
  else { mode = 'plate'; alpha = 0.8; }
  const eff = mode === 'plate' ? 0.06 : stats.mean * (1 - alpha);
  return { mode, alpha: Math.round(alpha * 100) / 100, contrast: Math.round(ratio(1, toLinear(eff)) * 10) / 10, measured: true };
}

function grab(args) {
  return new Promise((resolvePromise) => {
    const child = spawn('ffmpeg', ['-hide_banner', '-nostdin', '-v', 'error', ...args], { windowsHide: true });
    const chunks = [];
    child.stdout.on('data', (c) => chunks.push(c));
    child.on('error', () => resolvePromise(null));
    child.on('close', (code) => resolvePromise(code === 0 ? Buffer.concat(chunks) : null));
  });
}

/**
 * Sample each text scene's picture (stills once; videos at three points) at 1/6 scale, framed like `cover`.
 * scenes: [{id, file: {path, kind, duration}, at: [seconds in the media], band}] → {id: stats}
 */
export async function sampleScenes(scenes, fmt) {
  const scale = 6;
  const w = Math.round(fmt.W / scale), h = Math.round(fmt.H / scale);
  const vf = `scale=${w}:${h}:force_original_aspect_ratio=increase,crop=${w}:${h},format=gray`;
  const out = {};
  for (const s of scenes) {
    const times = s.file.kind === 'image' ? [null] : s.at;
    const all = [];
    for (const t of times) {
      const seek = t === null ? [] : ['-ss', String(Math.max(0, t).toFixed(3))];
      const buf = await grab([...seek, '-i', s.file.path, '-frames:v', '1', '-vf', vf, '-f', 'rawvideo', '-']);
      if (!buf || buf.length < w * h) continue;
      const st = regionStats(buf, w, h, s.band, scale);
      if (st) all.push(st);
    }
    if (!all.length) continue;
    // Worst case across samples: the brightest moment decides.
    out[s.id] = {
      mean: Math.max(...all.map((x) => x.mean)), p90: Math.max(...all.map((x) => x.p90)),
      p95: Math.max(...all.map((x) => x.p95)), std: Math.max(...all.map((x) => x.std)),
    };
  }
  return out;
}
