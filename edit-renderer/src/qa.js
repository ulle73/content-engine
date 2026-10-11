// Automatic technical QA of a rendered cut (ffmpeg only, no paid APIs): black frames, frozen frames, photosensitive
// flashes, clipped audio, silence gaps and loudness off target. The parsers are pure functions (tested on fixtures);
// technicalQa() runs two ffmpeg passes and turns the findings into Swedish warnings for the job.
const r2 = (n) => Math.round(n * 100) / 100;

/** blackdetect lines → [{start, end}] */
export function parseBlack(stderr) {
  return [...String(stderr).matchAll(/black_start:([\d.]+)\s+black_end:([\d.]+)/g)].map((m) => ({ start: Number(m[1]), end: Number(m[2]) }));
}

/** freezedetect lines → [{start, end}] (an open freeze runs to `duration`) */
export function parseFreeze(stderr, duration) {
  const out = [];
  let open = null;
  for (const line of String(stderr).split(/\r?\n/)) {
    const s = line.match(/lavfi\.freezedetect\.freeze_start:\s*([\d.]+)/);
    if (s) open = Number(s[1]);
    const e = line.match(/lavfi\.freezedetect\.freeze_end:\s*([\d.]+)/);
    if (e && open !== null) { out.push({ start: open, end: Number(e[1]) }); open = null; }
  }
  if (open !== null) out.push({ start: open, end: duration });
  return out;
}

/** metadata=print of signalstats.YAVG → [{t, y}] (y 0..255) */
export function parseLuma(stderr) {
  const out = [];
  let t = null;
  for (const line of String(stderr).split(/\r?\n/)) {
    const p = line.match(/pts_time:([\d.]+)/);
    if (p) t = Number(p[1]);
    const y = line.match(/lavfi\.signalstats\.YAVG=([\d.]+)/);
    if (y && t !== null) out.push({ t, y: Number(y[1]) });
  }
  return out;
}

/**
 * Photosensitive flashes (WCAG 2.3.1 "three flashes"): a flash is a pair of opposing luminance swings of more than
 * 10% of full range (~25/255); more than 3 flashes inside any 1 s window is a problem. Returns [{t, count}].
 */
export function findFlashes(luma, { delta = 25, window = 1, limit = 3 } = {}) {
  const swings = [];
  for (let i = 1; i < luma.length; i++) {
    const d = luma[i].y - luma[i - 1].y;
    if (Math.abs(d) >= delta) {
      const sign = Math.sign(d);
      const last = swings[swings.length - 1];
      if (!last || last.sign !== sign) swings.push({ t: luma[i].t, sign });
    }
  }
  const flashes = [];
  for (let i = 1; i < swings.length; i++) flashes.push(swings[i].t); // each opposing pair = one flash
  const out = [];
  for (let i = 0; i < flashes.length; i++) {
    const count = flashes.filter((t) => t >= flashes[i] && t < flashes[i] + window).length;
    if (count > limit && (!out.length || flashes[i] - out[out.length - 1].t >= window)) out.push({ t: r2(flashes[i]), count });
  }
  return out;
}

/** silencedetect → [{start, end}] */
export function parseSilence(stderr, duration) {
  const out = [];
  let open = null;
  for (const line of String(stderr).split(/\r?\n/)) {
    const s = line.match(/silence_start:\s*(-?[\d.]+)/);
    if (s) open = Math.max(0, Number(s[1]));
    const e = line.match(/silence_end:\s*([\d.]+)/);
    if (e && open !== null) { out.push({ start: open, end: Number(e[1]) }); open = null; }
  }
  if (open !== null) out.push({ start: open, end: duration });
  return out;
}

/** ebur128 summary → {I, LRA, TP} */
export function parseEbur128(stderr) {
  const text = String(stderr);
  const at = text.lastIndexOf('Summary:');
  const tail = at >= 0 ? text.slice(at) : text;
  const num = (re) => { const m = tail.match(re); return m ? Number(m[1]) : null; };
  return { I: num(/I:\s*(-?[\d.]+|-inf)\s*LUFS/), LRA: num(/LRA:\s*(-?[\d.]+)\s*LU/), TP: num(/Peak:\s*(-?[\d.]+|-inf)\s*dBFS/) };
}

/** astats overall → {peakDb, clipped (samples at full scale)} */
export function parseAstats(stderr) {
  const text = String(stderr);
  const at = text.lastIndexOf('Overall');
  const tail = at >= 0 ? text.slice(at) : text;
  const peak = tail.match(/Peak level dB:\s*(-?[\d.]+|-inf)/);
  const count = tail.match(/Peak count:\s*([\d.]+)/);
  const peakDb = peak ? Number(peak[1]) : null;
  return { peakDb: Number.isFinite(peakDb) ? peakDb + 0 : null, peakCount: count ? Number(count[1]) : 0 };
}

const inside = (seg, windows) => windows.some((w) => seg.start >= w.start - 0.05 && seg.end <= w.end + 0.05);

/**
 * Turn measurements into warnings. ctx: {duration, intentDark: [{start,end}], expectSound, targetLufs}
 * Returns {warnings, metrics}.
 */
export function judge(m, ctx) {
  const warnings = [];
  const D = ctx.duration;
  const black = (m.black || []).filter((s) => s.end - s.start >= 0.25 && !inside(s, ctx.intentDark || []));
  for (const s of black.slice(0, 3)) warnings.push(`QA: svart bild ${r2(s.start)}–${r2(s.end)} s.`);
  const frozen = (m.freeze || []).filter((s) => s.end - s.start >= 1.0 && !inside(s, ctx.intentStill || []));
  for (const s of frozen.slice(0, 3)) warnings.push(`QA: stillastående bild ${r2(s.start)}–${r2(s.end)} s (fryst klipp?).`);
  for (const f of (m.flashes || []).slice(0, 2)) warnings.push(`QA: ${f.count} blixtar inom en sekund vid ${f.t} s (risk för ljuskänsliga).`);
  const L = m.loudness || {};
  if (ctx.expectSound && L.I !== null && L.I !== undefined && Number.isFinite(L.I) && Math.abs(L.I - ctx.targetLufs) > 1.0) {
    warnings.push(`QA: ljudnivån är ${L.I} LUFS (mål ${ctx.targetLufs}).`);
  }
  if (L.TP !== null && L.TP !== undefined && L.TP > -0.5) warnings.push(`QA: ljudet når ${L.TP} dBTP – risk för klippning.`);
  else if ((m.astats?.peakDb ?? -99) >= -0.05 && (m.astats?.peakCount || 0) > 2) warnings.push('QA: ljudet klipper (toppar på 0 dBFS).');
  if (ctx.expectSound) {
    const gaps = (m.silence || []).filter((s) => s.end - s.start >= 0.6);
    if (gaps.length && gaps.some((s) => s.end - s.start >= D - 0.2)) warnings.push('QA: videon är helt tyst.');
    else for (const s of gaps.slice(0, 3)) warnings.push(`QA: tyst glapp ${r2(s.start)}–${r2(s.end)} s.`);
  }
  return {
    warnings,
    metrics: {
      black_s: r2(black.reduce((s, x) => s + x.end - x.start, 0)), frozen_s: r2(frozen.reduce((s, x) => s + x.end - x.start, 0)),
      flash_windows: (m.flashes || []).length, loudness_lufs: L.I ?? null, true_peak_dbtp: L.TP ?? null, lra: L.LRA ?? null,
      silence_s: r2((m.silence || []).reduce((s, x) => s + x.end - x.start, 0)),
    },
  };
}

/**
 * Run the detectors on a rendered file (the cut, without the brand outro). run: finish.run.
 * Returns {warnings, metrics} – never throws (a failing detector is skipped).
 */
export async function technicalQa(file, ctx, run) {
  const m = {};
  try {
    const video = await run('ffmpeg', ['-hide_banner', '-nostdin', '-loglevel', 'info', '-i', file, '-an', '-vf',
      'scale=270:-2,format=yuv420p,blackdetect=d=0.2:pix_th=0.10:pic_th=0.97,freezedetect=n=-55dB:d=0.9,signalstats,'
      + 'metadata=mode=print:key=lavfi.signalstats.YAVG', '-f', 'null', '-'], { timeoutMs: 5 * 60 * 1000 });
    m.black = parseBlack(video.stderr);
    m.freeze = parseFreeze(video.stderr, ctx.duration);
    m.flashes = findFlashes(parseLuma(video.stderr));
  } catch { /* skip video detectors */ }
  try {
    const audio = await run('ffmpeg', ['-hide_banner', '-nostdin', '-nostats', '-loglevel', 'info', '-i', file, '-vn', '-af',
      'asplit=3[a][b][c];[a]ebur128=peak=true[a1];[b]astats=metadata=0[b1];[c]silencedetect=n=-50dB:d=0.6[c1];[a1][b1][c1]amix=inputs=3',
      '-f', 'null', '-'], { timeoutMs: 5 * 60 * 1000 });
    m.loudness = parseEbur128(audio.stderr);
    m.astats = parseAstats(audio.stderr);
    m.silence = parseSilence(audio.stderr, ctx.duration);
  } catch { /* skip audio detectors */ }
  return judge(m, ctx);
}
