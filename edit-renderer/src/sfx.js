// Sound design: synthesized SFX (nothing to license – a JS port of library/prompts/motion-studio-playbook/sfx_synth.py,
// the repo's own synth, extended with the motion-studio sound vocabulary) and a cue mixer that writes one SFX stem.
// Cues come from compose.js (transitions, slams, explicit catalog sound ids, a riser into the brand outro).
import { writeFileSync } from 'node:fs';

export const SR = 48000;

/** Deterministic noise (mulberry32 + Box-Muller): the same cue always sounds the same. */
function rng(seed) {
  let a = seed >>> 0;
  const uni = () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  return () => Math.sqrt(-2 * Math.log(uni() + 1e-12)) * Math.cos(2 * Math.PI * uni());
}

const noise = (n, seed) => { const g = rng(seed); return Float64Array.from({ length: n }, g); };
const time = (dur) => Float64Array.from({ length: Math.round(dur * SR) }, (_, i) => i / SR);

/** Time-varying one-pole band-pass whose centre moves lo → hi → lo (the whoosh shape). */
function sweep(x, lo, hi, shape) {
  const n = x.length;
  const out = new Float64Array(n);
  let acc = 0, prev = 0;
  for (let i = 0; i < n; i++) {
    const s = shape ? shape(i / n) : Math.sin(Math.PI * i / n);
    const f = lo + (hi - lo) * s;
    const a = 1 - Math.exp((-2 * Math.PI * f) / SR);
    acc += a * (x[i] - acc);
    out[i] = (acc - prev) * 4;
    prev = acc;
  }
  return out;
}

function chirp(t, f) {
  // f(t) → sin of the integrated phase
  const out = new Float64Array(t.length);
  let ph = 0;
  for (let i = 0; i < t.length; i++) { ph += (2 * Math.PI * f(t[i])) / SR; out[i] = Math.sin(ph); }
  return out;
}

const SYNTH = {
  whoosh: (seed, dur = 0.5) => {
    const n = Math.round(dur * SR);
    const x = sweep(noise(n, seed), 300, 3000);
    return x.map((v, i) => v * Math.sin(Math.PI * i / n) ** 2);
  },
  swish: (seed, dur = 0.25) => {
    const n = Math.round(dur * SR);
    const x = sweep(noise(n, seed), 1200, 6000);
    return x.map((v, i) => v * Math.sin(Math.PI * i / n) ** 3);
  },
  impact: (seed, dur = 0.5) => {
    const t = time(dur);
    const body = chirp(t, (s) => 45 + 110 * Math.exp(-s * 30));
    const nz = noise(t.length, seed);
    return body.map((v, i) => (v * Math.exp(-t[i] * 9) + nz[i] * Math.exp(-t[i] * 60) * 0.35) * 0.9);
  },
  boom: (seed, dur = 0.9) => {
    const t = time(dur);
    const body = chirp(t, (s) => 35 + 70 * Math.exp(-s * 7));
    const nz = noise(t.length, seed);
    return body.map((v, i) => v * Math.exp(-t[i] * 4.5) * Math.min(1, t[i] / 0.004) + nz[i] * Math.exp(-t[i] * 40) * 0.2);
  },
  riser: (seed, dur = 1.4) => {
    const t = time(dur);
    const tone = chirp(t, (s) => 200 + 1800 * (s / dur) ** 2);
    const air = sweep(noise(t.length, seed), 400, 5000, (p) => p);
    return tone.map((v, i) => (v * 0.25 + air[i] * 0.5) * (t[i] / dur) ** 1.5 * Math.min(1, (dur - t[i]) / 0.012));
  },
  swell: (seed, dur = 1.0) => {
    // Reverse swell: soft filtered noise + a low tone that grows into the cut.
    const t = time(dur);
    const air = sweep(noise(t.length, seed), 200, 1800, (p) => p);
    const tone = t.map((s) => Math.sin(2 * Math.PI * 110 * s) * 0.3 + Math.sin(2 * Math.PI * 165 * s) * 0.15);
    return air.map((v, i) => (v * 0.6 + tone[i]) * (t[i] / dur) ** 2.2 * Math.min(1, (dur - t[i]) / 0.01));
  },
  pop: (seed, dur = 0.14) => {
    const t = time(dur);
    return chirp(t, (s) => 900 - (600 * s) / dur).map((v, i) => v * Math.min(1, t[i] / 0.003) * Math.exp(-25 * t[i]) * 0.8);
  },
  tick: (seed, dur = 0.03) => time(dur).map((s) => Math.sin(2 * Math.PI * 2600 * s) * (1 - s / dur) * 0.6),
  click: (seed, dur = 0.04) => {
    const t = time(dur);
    const nz = noise(t.length, seed);
    return t.map((s, i) => (Math.sin(2 * Math.PI * 1800 * s) * 0.5 + nz[i] * 0.3) * Math.exp(-90 * s));
  },
  snap: (seed, dur = 0.09) => {
    const t = time(dur);
    const nz = sweep(noise(t.length, seed), 2500, 7000, () => 1);
    return t.map((s, i) => (nz[i] * 0.6 + Math.sin(2 * Math.PI * 1300 * s) * 0.4) * Math.exp(-70 * s));
  },
  chime: (seed, dur = 1.2) => {
    const t = time(dur);
    return t.map((s) => [1046.5, 1318.5, 1568.0].reduce((acc, f, k) => acc + Math.sin(2 * Math.PI * f * s) * Math.exp(-s * (3 + k)), 0)
      * Math.min(1, s / 0.004) * 0.3);
  },
  shimmer: (seed, dur = 0.9) => {
    const t = time(dur);
    return t.map((s) => [2093, 2637, 3136, 4186].reduce((acc, f, k) => {
      const d = s - k * 0.07;
      return d >= 0 ? acc + Math.sin(2 * Math.PI * f * d) * Math.exp(-d * 7) : acc;
    }, 0) * 0.2);
  },
  tapestop: (seed, dur = 0.6) => {
    const t = time(dur);
    return chirp(t, (s) => 220 * (1 - s / dur) ** 1.6).map((v, i) => (v > 0 ? 1 : -1) * Math.abs(v) ** 0.7 * 0.4 * (1 - t[i] / dur));
  },
  'room-tone': (seed, dur = 2) => {
    const n = Math.round(dur * SR);
    const w = noise(n, seed);
    let b = 0;
    return w.map((v, i) => { b = b * 0.995 + v * 0.03; return b * Math.min(1, i / (0.3 * SR), (n - i) / (0.3 * SR)); });
  },
};
SYNTH.subdrop = SYNTH.boom;
SYNTH.sparkle = SYNTH.shimmer;

export const SFX_KINDS = Object.keys(SYNTH);

/** Peak gain (dBFS) per sound before the SFX bus fader: subtle accents that sit under the music. */
export const LEVEL_DB = {
  whoosh: -15, swish: -17, impact: -14, boom: -14, subdrop: -14, riser: -16, swell: -17, pop: -19, tick: -24, click: -22,
  snap: -20, chime: -20, shimmer: -21, sparkle: -21, tapestop: -18, 'room-tone': -36,
};

/** One sound, normalized to peak 0.9. Returns {data, peak (sample index)}. */
export function synth(kind, { seed = 1, dur } = {}) {
  const fn = SYNTH[kind];
  if (!fn) throw new Error(`okänt ljud ${kind}`);
  const x = fn(seed, dur);
  let peak = 0, at = 0;
  for (let i = 0; i < x.length; i++) if (Math.abs(x[i]) > peak) { peak = Math.abs(x[i]); at = i; }
  const k = peak > 0 ? 0.9 / peak : 0;
  return { data: x.map((v) => v * k), peak: at };
}

/**
 * Mix cues into one stereo float buffer of `duration` seconds.
 * cue: {kind, t, gainDb?, pan?: -1..1 | 'sweep', dur?, at?: 'peak' | 'start'}
 * The sound's peak lands 20 ms before t (a hit slightly early reads in sync; late reads broken); 'start' cues begin at t.
 */
export function mixCues(cues, duration, { lead = 0.02 } = {}) {
  const len = Math.max(1, Math.round(duration * SR));
  const L = new Float32Array(len), R = new Float32Array(len);
  cues.forEach((cue, idx) => {
    const { data, peak } = synth(cue.kind, { seed: 1000 + idx * 7919, dur: cue.dur });
    const gain = 10 ** ((cue.gainDb ?? LEVEL_DB[cue.kind] ?? -18) / 20);
    const start = cue.at === 'start' ? Math.round(cue.t * SR) : Math.round((cue.t - lead) * SR) - peak;
    for (let i = 0; i < data.length; i++) {
      const j = start + i;
      if (j < 0 || j >= len) continue;
      const p = cue.pan === 'sweep' ? -0.7 + 1.4 * (i / data.length) : Number(cue.pan || 0);
      const v = data[i] * gain;
      L[j] += v * Math.min(1, 1 - p);
      R[j] += v * Math.min(1, 1 + p);
    }
  });
  let peak = 0;
  for (let i = 0; i < len; i++) peak = Math.max(peak, Math.abs(L[i]), Math.abs(R[i]));
  if (peak > 0.89) { const k = 0.89 / peak; for (let i = 0; i < len; i++) { L[i] *= k; R[i] *= k; } }
  return { L, R, peak };
}

/** 32-bit float stereo WAV. */
export function writeWav(path, { L, R }) {
  const n = L.length;
  const data = Buffer.alloc(n * 8);
  for (let i = 0; i < n; i++) { data.writeFloatLE(L[i], i * 8); data.writeFloatLE(R[i], i * 8 + 4); }
  const h = Buffer.alloc(44);
  h.write('RIFF', 0); h.writeUInt32LE(36 + data.length, 4); h.write('WAVE', 8); h.write('fmt ', 12);
  h.writeUInt32LE(16, 16); h.writeUInt16LE(3, 20); h.writeUInt16LE(2, 22); h.writeUInt32LE(SR, 24);
  h.writeUInt32LE(SR * 8, 28); h.writeUInt16LE(8, 32); h.writeUInt16LE(32, 34); h.write('data', 36); h.writeUInt32LE(data.length, 40);
  writeFileSync(path, Buffer.concat([h, data]));
}

/** Transition → accent sound (null = no sound; soft dissolves stay quiet). */
export const TRANSITION_SFX = {
  whip: { kind: 'whoosh', pan: 'sweep' }, push: { kind: 'whoosh', pan: 'sweep' }, zoom: { kind: 'whoosh' },
  wipe: { kind: 'swish', pan: 'sweep' }, iris: { kind: 'swish' }, flash: { kind: 'impact', gainDb: -17 },
  glitch: { kind: 'click', gainDb: -20 }, 'light-leak': { kind: 'shimmer' }, 'speed-ramp': { kind: 'whoosh', pan: 'sweep' },
  fade: null, blur: null, cut: null,
};
