// Beat-synced editing: find the music's beat grid, then snap scene boundaries (and with them the transitions) to it.
// Detection: `hyperframes beats --json` on a one-track project (preferred), else an ffmpeg decode + spectral-flux onset
// detector in plain JS. Both yield onsets; beatGrid() turns onsets into a steady grid with tempo, phase and downbeats.
import { spawn } from 'node:child_process';
import { copyFileSync, existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { basename, extname, join } from 'node:path';

const r3 = (n) => Math.round(n * 1000) / 1000;

// ------------------------------------------------------------------------------------------------ detection

/** Run `hyperframes beats` on a throwaway project holding only the music. Returns [{t, s}] or null. */
async function hyperframesOnsets(music, workDir, duration, { run, hyperframes }) {
  const dir = join(workDir, 'beats-project');
  rmSync(dir, { recursive: true, force: true });
  mkdirSync(dir, { recursive: true });
  const name = `music${extname(music).toLowerCase() || '.wav'}`;
  copyFileSync(music, join(dir, name));
  const d = Math.max(1, Math.ceil(duration || 60));
  writeFileSync(join(dir, 'index.html'), `<!doctype html>
<html><head><meta charset="UTF-8"></head><body>
<div id="root" data-composition-id="main" data-start="0" data-duration="${d}" data-width="1080" data-height="1920">
<audio id="music" src="${name}" data-start="0" data-duration="${d}" data-track-index="1"></audio>
</div><script>window.__timelines = window.__timelines || {};</script></body></html>
`);
  const res = await run('npx', ['--yes', hyperframes, 'beats', dir, '--json'], { timeoutMs: 120000 });
  const file = join(dir, 'beats', `${name}.json`);
  if (res.code !== 0 || !existsSync(file)) return null;
  const data = JSON.parse(readFileSync(file, 'utf8'));
  const onsets = (data.beats || []).map((b) => ({ t: Number(b.time), s: Number(b.strength ?? 1) })).filter((b) => Number.isFinite(b.t));
  return onsets.length ? onsets : null;
}

function decodeMono(music, sampleRate, seconds) {
  return new Promise((resolvePromise, reject) => {
    const args = ['-hide_banner', '-nostdin', '-v', 'error', '-i', music, '-t', String(seconds), '-ac', '1', '-ar', String(sampleRate), '-f', 'f32le', '-'];
    const child = spawn('ffmpeg', args, { windowsHide: true });
    const chunks = [];
    child.stdout.on('data', (c) => chunks.push(c));
    child.on('error', reject);
    child.on('close', (code) => {
      if (code !== 0) return reject(new Error(`ffmpeg avkodning misslyckades (${code})`));
      const buf = Buffer.concat(chunks);
      resolvePromise(new Float32Array(buf.buffer, buf.byteOffset, Math.floor(buf.length / 4)));
    });
  });
}

function fft(re, im) {
  const n = re.length;
  for (let i = 1, j = 0; i < n; i++) {
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) { [re[i], re[j]] = [re[j], re[i]]; [im[i], im[j]] = [im[j], im[i]]; }
  }
  for (let len = 2; len <= n; len <<= 1) {
    const ang = (-2 * Math.PI) / len;
    const wr = Math.cos(ang), wi = Math.sin(ang);
    for (let i = 0; i < n; i += len) {
      let cr = 1, ci = 0;
      for (let k = 0; k < len / 2; k++) {
        const a = i + k, b = a + len / 2;
        const tr = re[b] * cr - im[b] * ci, ti = re[b] * ci + im[b] * cr;
        re[b] = re[a] - tr; im[b] = im[a] - ti; re[a] += tr; im[a] += ti;
        const nr = cr * wr - ci * wi; ci = cr * wi + ci * wr; cr = nr;
      }
    }
  }
}

/** Spectral-flux onsets from mono PCM. Returns [{t, s}] with s normalized to 0..1. */
export function onsetsFromPcm(pcm, sampleRate) {
  const N = 1024, hop = 256;
  const win = Float32Array.from({ length: N }, (_, i) => 0.5 - 0.5 * Math.cos((2 * Math.PI * i) / N));
  const frames = Math.max(0, Math.floor((pcm.length - N) / hop));
  const flux = new Float32Array(frames);
  let prev = new Float32Array(N / 2);
  const re = new Float32Array(N), im = new Float32Array(N);
  for (let f = 0; f < frames; f++) {
    for (let i = 0; i < N; i++) { re[i] = pcm[f * hop + i] * win[i]; im[i] = 0; }
    fft(re, im);
    const mag = new Float32Array(N / 2);
    let sum = 0;
    for (let k = 1; k < N / 2; k++) {
      mag[k] = Math.log1p(100 * Math.hypot(re[k], im[k]));
      const d = mag[k] - prev[k];
      if (d > 0) sum += d;
    }
    flux[f] = sum;
    prev = mag;
  }
  const fps = sampleRate / hop;
  const max = flux.reduce((m, v) => Math.max(m, v), 0) || 1;
  const out = [];
  const w = Math.round(0.1 * fps);
  let last = -1;
  for (let f = 3; f < frames - 3; f++) {
    const v = flux[f];
    let isPeak = true;
    for (let k = -3; k <= 3; k++) if (k && flux[f + k] > v) { isPeak = false; break; }
    if (!isPeak) continue;
    let mean = 0, c = 0;
    for (let k = Math.max(0, f - w); k < Math.min(frames, f + w); k++) { mean += flux[k]; c++; }
    mean /= c || 1;
    if (v < mean * 1.15 + 0.06 * max) continue;
    const t = (f * hop + N) / sampleRate; // calibrated: flux peaks as the attack fills the window
    if (last >= 0 && t - last < 0.1) continue;
    out.push({ t: r3(t), s: Math.min(1, v / max) });
    last = t;
  }
  return out;
}

async function ffmpegOnsets(music, duration) {
  const sr = 22050;
  const pcm = await decodeMono(music, sr, Math.min(600, Math.max(5, (duration || 90) + 1)));
  const onsets = onsetsFromPcm(pcm, sr);
  return onsets.length ? onsets : null;
}

/**
 * Detect the beat grid for a music file. ctx: {run, hyperframes, log}. Returns grid (see beatGrid) + {source} or null.
 */
export async function detectBeats(music, workDir, duration, ctx) {
  let onsets = null;
  let source = 'hyperframes';
  try {
    onsets = await hyperframesOnsets(music, workDir, duration, ctx);
  } catch (err) {
    ctx.log?.(`beats: hyperframes beats misslyckades (${err.message}); använder ffmpeg`);
  }
  if (!onsets) {
    source = 'ffmpeg';
    try {
      onsets = await ffmpegOnsets(music, duration);
    } catch (err) {
      ctx.log?.(`beats: ffmpeg-analysen misslyckades (${err.message})`);
      return null;
    }
  }
  const grid = onsets && beatGrid(onsets, duration);
  return grid ? { ...grid, source, file: basename(music) } : null;
}

// ------------------------------------------------------------------------------------------------ grid

/**
 * Onsets [{t, s}] → steady grid {bpm, period, offset, confidence, beats: [{t, down, s}]} or null when there is no
 * usable pulse (fewer than 8 onsets or a weak match).
 */
export function beatGrid(onsets, duration) {
  const list = (onsets || []).filter((o) => o.t >= 0).sort((a, b) => a.t - b.t);
  if (list.length < 8) return null;
  const end = Math.max(duration || 0, list[list.length - 1].t + 0.5);
  const R = 100; // envelope resolution (Hz)
  const env = new Float32Array(Math.ceil(end * R) + 2);
  for (const o of list) {
    const i = Math.round(o.t * R);
    env[i] += o.s;
    if (i > 0) env[i - 1] += o.s * 0.5;
    env[i + 1] += o.s * 0.5;
  }
  // Tempo: autocorrelation over 60–180 BPM, weighted towards ~110 BPM (log-normal prior) to avoid double/half tempo.
  let bestL = 0, bestScore = -1;
  const scores = {};
  for (let L = 33; L <= 100; L++) {
    let s = 0;
    for (let i = 0; i + L < env.length; i++) s += env[i] * env[i + L];
    const prior = Math.exp(-0.5 * (Math.log2(L / 55) / 0.75) ** 2);
    scores[L] = s;
    if (s * prior > bestScore) { bestScore = s * prior; bestL = L; }
  }
  const a = scores[bestL - 1] ?? scores[bestL], b = scores[bestL], c = scores[bestL + 1] ?? scores[bestL];
  const denom = a - 2 * b + c;
  let period = (bestL + (denom ? (0.5 * (a - c)) / denom : 0)) / R;
  // Phase: the offset whose grid collects the most onset strength.
  const near = (t, tol) => {
    let best = 0;
    for (const o of list) {
      if (o.t < t - tol) continue;
      if (o.t > t + tol) break;
      best = Math.max(best, o.s * (1 - Math.abs(o.t - t) / tol));
    }
    return best;
  };
  let offset = 0, phaseScore = -1;
  for (let phi = 0; phi < period; phi += 0.005) {
    let s = 0;
    for (let t = phi; t <= end; t += period) s += near(t, 0.05);
    if (s > phaseScore) { phaseScore = s; offset = phi; }
  }
  // Refine period and phase with a least-squares fit of the matched onsets (removes slow drift).
  const matched = [];
  for (let k = 0; offset + k * period <= end; k++) {
    const t = offset + k * period;
    let hit = null;
    for (const o of list) {
      if (Math.abs(o.t - t) <= 0.06 && (!hit || Math.abs(o.t - t) < Math.abs(hit.t - t))) hit = o;
      if (o.t > t + 0.06) break;
    }
    if (hit) matched.push([k, hit.t]);
  }
  if (matched.length >= 6) {
    const n = matched.length;
    const mk = matched.reduce((s, m) => s + m[0], 0) / n, mt = matched.reduce((s, m) => s + m[1], 0) / n;
    let num = 0, den = 0;
    for (const [k, t] of matched) { num += (k - mk) * (t - mt); den += (k - mk) ** 2; }
    if (den > 0) {
      const p = num / den;
      if (Math.abs(p - period) < period * 0.05) { period = p; offset = mt - p * mk; }
    }
  }
  while (offset - period >= -0.02) offset -= period;
  if (offset < 0) offset += period;
  const beats = [];
  for (let k = 0; offset + k * period <= end + 1e-6; k++) {
    const t = offset + k * period;
    beats.push({ t: r3(t), s: Math.round(near(t, 0.06) * 1000) / 1000, k });
  }
  const lastOnset = list[list.length - 1].t;
  const musical = beats.filter((x) => x.t <= lastOnset + 0.05);
  const confidence = musical.length ? musical.filter((x) => x.s > 0).length / musical.length : 0;
  if (confidence < 0.35) return null;
  // Downbeats: the bar phase (4/4) whose beats carry the most strength.
  let bar = 0, barScore = -1;
  for (let m = 0; m < 4; m++) {
    const s = beats.filter((x) => x.k % 4 === m).reduce((sum, x) => sum + x.s, 0);
    if (s > barScore + 1e-9) { barScore = s; bar = m; }
  }
  return {
    bpm: Math.round((60 / period) * 10) / 10, period: r3(period), offset: r3(offset), confidence: Math.round(confidence * 100) / 100,
    beats: beats.map((x) => ({ t: x.t, down: x.k % 4 === bar, s: x.s })),
  };
}

// ------------------------------------------------------------------------------------------------ snapping

/**
 * Snap scene boundaries to beats.
 *   scenes: [{id, duration, max?}] in film order (max: longest the scene may become, e.g. remaining video length)
 *   grid: beatGrid() result
 * Rules: each boundary moves at most `tolerance` s (≤ 0.6 beat); a scene never gets shorter than 0.8 s (or shorter at
 * all if it already was); the end of the last scene moves at most `totalSlack` s, so the film length stays within it.
 * Downbeats are preferred over other beats when both are close. Returns {durations, snaps, tolerance}.
 */
export function snapScenes(scenes, grid, { tolerance = 0.3, minScene = 0.8, totalSlack = 0.3 } = {}) {
  const n = scenes.length;
  const durations = scenes.map((s) => Number(s.duration));
  if (!grid || !grid.beats?.length || !n) return { durations, snaps: [], tolerance: 0 };
  const tol = Math.min(tolerance, grid.period * 0.6);
  const orig = [0];
  for (const d of durations) orig.push(orig[orig.length - 1] + d);
  // Candidates per boundary k = 1..n: stay, or any beat inside the window.
  const cands = [[{ t: 0, cost: 0, beat: null }]];
  for (let k = 1; k <= n; k++) {
    const B = orig[k];
    const win = k === n ? Math.min(tol, totalSlack) : tol;
    const list = [{ t: B, cost: win + 0.05, beat: null }];
    for (const b of grid.beats) {
      const d = Math.abs(b.t - B);
      if (d <= win + 1e-9) list.push({ t: b.t, cost: d - (b.down ? 0.06 : 0) - (b.s > 0 ? 0.02 : 0), beat: b });
    }
    cands.push(list);
  }
  const minFor = (i) => Math.min(durations[i], Math.max(minScene, 0));
  const maxFor = (i) => (Number.isFinite(scenes[i].max) ? Math.max(scenes[i].max, durations[i]) : Infinity);
  // DP over boundaries.
  let prevCost = [0];
  const back = [[-1]];
  for (let k = 1; k <= n; k++) {
    const cur = new Array(cands[k].length).fill(Infinity);
    const bk = new Array(cands[k].length).fill(-1);
    cands[k].forEach((c, ci) => {
      cands[k - 1].forEach((p, pi) => {
        if (prevCost[pi] === Infinity) return;
        const len = c.t - p.t;
        if (len < minFor(k - 1) - 1e-6 || len > maxFor(k - 1) + 1e-6) return;
        const total = prevCost[pi] + c.cost;
        if (total < cur[ci]) { cur[ci] = total; bk[ci] = pi; }
      });
    });
    prevCost = cur;
    back.push(bk);
  }
  let ci = prevCost.reduce((bi, v, i, arr) => (v < arr[bi] ? i : bi), 0);
  if (prevCost[ci] === Infinity) return { durations, snaps: [], tolerance: tol };
  const chosen = new Array(n + 1);
  for (let k = n; k >= 1; k--) { chosen[k] = cands[k][ci]; ci = back[k][ci]; }
  chosen[0] = cands[0][0];
  const snaps = [];
  const out = [];
  for (let k = 1; k <= n; k++) {
    out.push(r3(chosen[k].t - chosen[k - 1].t));
    if (chosen[k].beat && Math.abs(chosen[k].t - orig[k]) > 0.0005) {
      snaps.push({ after: scenes[k - 1].id, from: r3(orig[k]), to: r3(chosen[k].t), delta: r3(chosen[k].t - orig[k]), down: chosen[k].beat.down });
    } else if (chosen[k].beat) {
      snaps.push({ after: scenes[k - 1].id, from: r3(orig[k]), to: r3(chosen[k].t), delta: 0, down: chosen[k].beat.down });
    }
  }
  return { durations: out, snaps, tolerance: r3(tol) };
}

/** The beat to land an entrance on: nearest in [t - before, t + after] (downbeats win ties), else t. */
export function alignToBeat(t, grid, { before = 0.06, after = 0.35 } = {}) {
  if (!grid?.beats?.length) return t;
  let best = null;
  for (const b of grid.beats) {
    if (b.t < t - before) continue;
    if (b.t > t + after) break;
    const score = Math.abs(b.t - t) - (b.down ? 0.05 : 0);
    if (!best || score < best.score) best = { t: b.t, score };
  }
  return best ? best.t : t;
}

export function beatsBetween(grid, a, b, { down = false } = {}) {
  if (!grid?.beats) return [];
  return grid.beats.filter((x) => x.t >= a && x.t <= b && (!down || x.down)).map((x) => x.t);
}

/** Mean distance (s) from each cut to its nearest beat – the measured "on-beat" quality. */
export function beatError(cuts, grid) {
  if (!grid?.beats?.length || !cuts.length) return null;
  const errs = cuts.map((t) => Math.min(...grid.beats.map((b) => Math.abs(b.t - t))));
  return r3(errs.reduce((s, e) => s + e, 0) / errs.length);
}
