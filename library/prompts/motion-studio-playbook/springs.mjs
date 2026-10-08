// springs.mjs — closed-form motion math for seek(t)-driven films (content-engine, egen implementation).
//
// Everything here is a pure function of time: no integrators, no state between frames, so any frame
// can be rendered alone, in parallel, out of order. Works in the browser (<script type="module">)
// and in Node (import).
//
//   springFrom(t, x0, v0, target, opts)  value of a damped spring released at t=0 from x0 with velocity v0
//   springStep(t, opts)                  0 -> 1 step response (t = seconds since the change)
//   springVel(t, opts)                   d/dt of springStep (useful for loop-seam velocity checks)
//   track(t, keys, opts)                 a value that changes target many times = sum of one spring per change
//   trackObj(t, keys, opts)              same for objects {x, y, w, h, r, ...} (every numeric field)
//   hold(t, keys)                        step function (no spring) – for discrete states (text, icon id)
//   hash(seed, i) / rand(seed, i)        integer hash -> [0,1)
//   noise1(x, seed)                      smooth 1-D value noise in [0,1]
//   boil(t, rate, seed)                  seed that changes `rate` times per second (hand-drawn "boil")
//   beatInfo(t, beats)                   {index, since, phase} for a sorted list of beat times
//   pulse(t, beats, decay)               1 on each beat, decaying exponentially – for on-beat bumps
//
// Spring options: { freq: Hz (natural frequency, default 2.2), zeta: damping ratio (default 0.75) }
//   zeta < 1 overshoots (0.5 = lively, 0.8 = "a tiny overshoot at most"), zeta = 1 critically damped, > 1 sluggish.
//   Roughly: settle time ≈ 4 / (zeta * 2π * freq) seconds.

const TAU = Math.PI * 2;

/** Damped spring released at t=0 from x0 with velocity v0, pulled towards `target`. Pure function of t. */
export function springFrom(t, x0, v0, target, { freq = 2.2, zeta = 0.75 } = {}) {
  if (t <= 0) return x0;
  const w = TAU * freq;
  const c1 = x0 - target;
  if (zeta < 1) {
    const wd = w * Math.sqrt(1 - zeta * zeta);
    const c2 = (v0 + zeta * w * c1) / wd;
    return target + Math.exp(-zeta * w * t) * (c1 * Math.cos(wd * t) + c2 * Math.sin(wd * t));
  }
  if (zeta === 1) {
    const c2 = v0 + w * c1;
    return target + Math.exp(-w * t) * (c1 + c2 * t);
  }
  const s = Math.sqrt(zeta * zeta - 1);
  const r1 = -w * (zeta - s);
  const r2 = -w * (zeta + s);
  // x(t) = target + A e^{r1 t} + B e^{r2 t},  A + B = c1,  A r1 + B r2 = v0
  const b = (v0 - r1 * c1) / (r2 - r1);
  const a = c1 - b;
  return target + a * Math.exp(r1 * t) + b * Math.exp(r2 * t);
}

/** Step response 0 -> 1 (t = seconds since the change). */
export function springStep(t, opts) {
  return springFrom(t, 0, 0, 1, opts);
}

/** Derivative of springStep, numerically (central difference, 1 ms). */
export function springVel(t, opts) {
  const h = 1e-3;
  return (springStep(t + h, opts) - springStep(Math.max(0, t - h), opts)) / (t > h ? 2 * h : t + h);
}

/**
 * A value that is retargeted many times: v(t) = v0 + Σ (v_i - v_{i-1}) · springStep(t - t_i).
 * Because a linear spring obeys superposition this is exactly what one spring would do if its target
 * jumped at each key – including retargeting mid-flight – but it stays a pure function of t.
 * keys: [{ t: seconds, v: value, spring?: {freq, zeta} }, ...] sorted by t. The first key is the start value.
 */
export function track(t, keys, opts) {
  if (!keys.length) return 0;
  let value = keys[0].v;
  for (let i = 1; i < keys.length; i++) {
    const k = keys[i];
    if (t <= k.t) break;
    value += (k.v - keys[i - 1].v) * springStep(t - k.t, k.spring || opts);
  }
  return value;
}

/** track() for objects: every numeric field of the keys' `v` objects gets its own track. */
export function trackObj(t, keys, opts) {
  const out = {};
  for (const field of Object.keys(keys[0].v)) {
    out[field] = track(t, keys.map((k) => ({ t: k.t, v: k.v[field], spring: k.spring })), opts);
  }
  return out;
}

/** Discrete state at time t (last key with k.t <= t). */
export function hold(t, keys) {
  let value = keys[0].v;
  for (const k of keys) if (k.t <= t) value = k.v;
  return value;
}

/** 32-bit integer hash of (seed, i) -> [0, 1). Stable across runs and machines. */
export function hash(seed, i = 0) {
  let x = (Math.imul(seed | 0, 0x9e3779b1) ^ Math.imul(i | 0, 0x85ebca77)) >>> 0;
  x ^= x >>> 16; x = Math.imul(x, 0x7feb352d) >>> 0;
  x ^= x >>> 15; x = Math.imul(x, 0x846ca68b) >>> 0;
  x ^= x >>> 16;
  return (x >>> 0) / 4294967296;
}
export const rand = hash;

/** Smooth 1-D value noise in [0, 1] (smoothstep between hashed lattice points). */
export function noise1(x, seed = 1) {
  const i = Math.floor(x);
  const f = x - i;
  const u = f * f * (3 - 2 * f);
  return hash(seed, i) * (1 - u) + hash(seed, i + 1) * u;
}

/** A seed that changes `rate` times per second – feed it to hash() for hand-drawn line "boil". */
export function boil(t, rate = 12, seed = 1) {
  return (seed * 1000003 + Math.floor(t * rate)) | 0;
}

/** Position of t relative to a sorted list of beat times (seconds). */
export function beatInfo(t, beats) {
  let index = -1;
  for (let i = 0; i < beats.length; i++) if (beats[i] <= t) index = i; else break;
  if (index < 0) return { index: -1, since: t - (beats[0] ?? 0), phase: 0 };
  const next = beats[index + 1] ?? beats[index] + (beats[index] - (beats[index - 1] ?? beats[index] - 0.5));
  const since = t - beats[index];
  return { index, since, phase: since / Math.max(1e-6, next - beats[index]) };
}

/** 1 exactly on a beat, decaying with time constant `decay` seconds – multiply into scale/glow for on-beat hits. */
export function pulse(t, beats, decay = 0.12) {
  const { index, since } = beatInfo(t, beats);
  return index < 0 ? 0 : Math.exp(-since / decay);
}
