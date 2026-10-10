// Finish-quality units: beat grid + snapping, Swedish line breaking, safe zones, legibility, SFX, QA detectors.
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';

import { alignToBeat, beatError, beatGrid, onsetsFromPcm, snapScenes } from '../src/beats.js';
import { judgeCheck, layoutReport } from '../src/check.js';
import { chunkWords, compose, lookMatrix, planSfx, words } from '../src/compose.js';
import { legibility, regionStats } from '../src/legibility.js';
import { findFlashes, judge, parseAstats, parseBlack, parseEbur128, parseFreeze, parseLuma, parseSilence } from '../src/qa.js';
import { FORMATS, PLATFORM_ZONES, checkSafeZones, marginsCoverZones } from '../src/safezones.js';
import { LEVEL_DB, SFX_KINDS, SR, mixCues, synth } from '../src/sfx.js';
import { SUPPORT } from '../src/support.js';
import { breakLines, planLines, resolveBrandFonts, sizeSteps } from '../src/typeset.js';

const tmp = mkdtempSync(join(tmpdir(), 'cut-quality-'));
process.on('exit', () => rmSync(tmp, { recursive: true, force: true }));

/** Onsets of a 120 BPM track starting at 0.5 s: strong on the beat, weak 16ths in between, louder downbeats. */
function onsets120(seconds = 20) {
  const out = [];
  for (let k = 0; 0.5 + k * 0.5 < seconds; k++) {
    const t = 0.5 + k * 0.5;
    out.push({ t: t + (k % 3 === 0 ? 0.008 : -0.006), s: k % 4 === 0 ? 1 : 0.7 });
    out.push({ t: t + 0.11, s: 0.45 });
  }
  return out;
}

// ------------------------------------------------------------------ beats
test('beat grid finds tempo, phase and downbeats from onsets', () => {
  const g = beatGrid(onsets120(), 20);
  assert.ok(Math.abs(g.bpm - 120) < 1, `bpm ${g.bpm}`);
  assert.ok(Math.abs(g.period - 0.5) < 0.01);
  assert.ok(g.confidence > 0.9);
  const near = (t) => g.beats.reduce((b, x) => (Math.abs(x.t - t) < Math.abs(b.t - t) ? x : b));
  assert.ok(Math.abs(near(2.5).t - 2.5) < 0.02);
  // Downbeats every 4 beats, on the loud onsets (0.5, 2.5, 4.5 …).
  assert.ok(near(2.5).down && near(4.5).down && !near(3.0).down);
  assert.equal(beatGrid([{ t: 1, s: 1 }, { t: 2, s: 1 }], 5), null);
});

test('spectral-flux onsets from PCM clicks', () => {
  const sr = 22050;
  const pcm = new Float32Array(sr * 4);
  for (let k = 0; k < 8; k++) {
    const at = Math.round((0.25 + k * 0.5) * sr);
    for (let i = 0; i < 400; i++) pcm[at + i] = Math.sin(i * 0.9) * Math.exp(-i / 80);
  }
  const on = onsetsFromPcm(pcm, sr);
  assert.ok(on.length >= 7 && on.length <= 9, `${on.length} onsets`);
  for (const o of on) assert.ok(Math.abs(((o.t - 0.25) % 0.5 + 0.5) % 0.5) < 0.06 || Math.abs(((o.t - 0.25) % 0.5) - 0.5) < 0.06, `onset ${o.t}`);
});

test('scene boundaries snap to beats within tolerance, keep length and minimum scene length', () => {
  const g = beatGrid(onsets120(), 20);
  const scenes = [2.6, 3.0, 3.0, 2.6].map((d, i) => ({ id: `s${i + 1}`, duration: d }));
  const res = snapScenes(scenes, g);
  const ends = res.durations.reduce((a, d) => [...a, (a.at(-1) || 0) + d], []);
  for (const t of ends) assert.ok(g.beats.some((b) => Math.abs(b.t - t) < 0.002), `cut ${t} on a beat`);
  const total = ends.at(-1);
  assert.ok(Math.abs(total - 11.2) <= 0.3 + 1e-9, `total ${total}`);
  assert.ok(res.durations.every((d) => d >= 0.8));
  assert.equal(res.snaps.length, 4);
  assert.ok(beatError(ends, g) < beatError([2.6, 5.6, 8.6, 11.2], g));
  // Never below 0.8 s, never shorter at all when already short, never past the end of a video.
  const short = snapScenes([{ id: 'a', duration: 0.6 }, { id: 'b', duration: 0.85 }, { id: 'c', duration: 2 }], g);
  assert.ok(short.durations[0] >= 0.6 - 1e-9 && short.durations[1] >= 0.8 - 1e-9);
  const capped = snapScenes([{ id: 'a', duration: 2.3, max: 2.3 }, { id: 'b', duration: 2 }], g);
  assert.ok(capped.durations[0] <= 2.3 + 1e-9);
  // Without a grid nothing moves.
  assert.deepEqual(snapScenes(scenes, null).durations, [2.6, 3.0, 3.0, 2.6]);
});

test('entrances land on the nearest beat ahead', () => {
  const g = beatGrid(onsets120(), 20);
  const at = alignToBeat(2.38, g);
  assert.ok(Math.abs(at - 2.5) < 0.02);
  assert.equal(alignToBeat(2.38, null), 2.38);
});

test('compose snaps the cut to the music and records the snaps', () => {
  const g = beatGrid(onsets120(), 20);
  const img = join(tmp, 'still.jpg');
  writeFileSync(img, 'x');
  const spec = {
    schema: 'cut/v1', format: '9:16', fps: 30, title: 'Takt', music_asset_id: 'm', music_volume: 1, cta: null,
    scenes: [2.6, 3.0, 2.7].map((d, i) => ({ id: `s${i + 1}`, purpose: i ? 'body' : 'hook', duration_s: d, asset_id: 'img', fit: 'cover',
      text: 'Över *400 klubbar*', text_style: null, effects: i === 1 ? ['hyperframes.registry.beat-freeze-cut'] : [],
      transition_in: i ? 'hyperframes.registry.whip-pan' : null })),
  };
  const r = compose({ spec, files: { img: { path: img, kind: 'image' } }, outDir: join(tmp, 'beat'), beats: g, outro: true });
  assert.ok(Math.abs(r.total - 8.3) <= 0.3);
  for (const s of r.config.scenes.slice(1)) assert.ok(g.beats.some((b) => Math.abs(b.t - s.start) < 0.002));
  assert.ok(r.config.beats.times.length > 10);
  assert.ok(r.timing.snaps.length >= 2);
  // Whip gets a whoosh on the cut, the outro a riser that ends where the cut ends.
  assert.ok(r.sfx.some((c) => c.kind === 'whoosh' && Math.abs(c.t - r.config.scenes[1].start) < 1e-6));
  assert.ok(r.sfx.some((c) => c.kind === 'riser' && c.t === r.total));
  assert.ok(r.config.scenes[1].effects.includes('beat-punch'));
  const html = readFileSync(join(tmp, 'beat', 'index.html'), 'utf8');
  assert.match(html, /<filter id="MBI-s2"/);
  assert.match(html, /const breakLines = function breakLines/);
});

// ------------------------------------------------------------------ typography
test('balanced Swedish line breaks: no orphans, no dangling function words, char limit', () => {
  const opts = { size: 100, maxW: 760, maxChars: 22 };
  const hook = planLines('Din chef betalar din golf', { ...opts, condensed: true, size: 172 });
  assert.ok(hook.length >= 2);
  assert.ok(hook.at(-1).includes(' '), `orphan: ${JSON.stringify(hook)}`);
  const lines = planLines('Boka på två minuter', { ...opts, size: 88 });
  assert.notDeepEqual(lines, ['Boka på två', 'minuter']);
  assert.ok(lines.at(-1).split(' ').length >= 2);
  // Numbers stay with their unit.
  for (const l of planLines('Över 400 klubbar i hela Sverige att välja mellan', { ...opts, size: 88 })) assert.ok(!/\b400$/.test(l));
  // Never more than maxChars on a line (unless a single word).
  for (const l of planLines('Friskvårdsbidraget räcker till greenfee på fler än fyrahundra klubbar', { ...opts, size: 60, maxW: 2000 })) {
    assert.ok(l.length <= 22 || !l.includes(' '), l);
  }
  // Too wide words → null so the caller shrinks the type.
  assert.equal(breakLines([900], 20, 760, { texts: ['Friskvårdsbidraget'] }), null);
  // Balanced: two similar lines beat a long + short split.
  const res = breakLines([100, 100, 100, 100], 10, 330, { texts: ['aa', 'bb', 'cc', 'dd'] });
  assert.deepEqual(res.lines, [[0, 2], [2, 4]]);
});

test('type scale and brand fonts', () => {
  const steps = sizeSteps('9:16', 'slam', 'center', 1080, 1920);
  assert.equal(steps[0], 172);
  assert.ok(steps.every((v, i) => !i || v < steps[i - 1]));
  assert.deepEqual(resolveBrandFonts('Inter, Arial, sans-serif'), { text: 'inter', display: 'anton', warning: null });
  assert.equal(resolveBrandFonts('Playfair Display, Georgia, serif').text, 'playfair display');
  assert.equal(resolveBrandFonts('Caveat Brush').display, 'caveat brush');
  assert.match(resolveBrandFonts('Comic Neue').warning, /Comic Neue/);
  assert.deepEqual(chunkWords(words('Boka din golf på två minuter idag')).map((c) => c.map((w) => w.text).join(' ')),
    ['Boka din golf', 'på två minuter idag']);
});

// ------------------------------------------------------------------ safe zones
test('platform safe zones: margins cover them and violations are found', () => {
  for (const f of Object.keys(FORMATS)) assert.ok(marginsCoverZones(f), f);
  assert.equal(PLATFORM_ZONES['9:16'].bottom, 0.22);
  assert.deepEqual(checkSafeZones([{ id: 'ok', x: 120, y: 700, w: 700, h: 300 }], '9:16'), []);
  const hits = checkSafeZones([{ id: 'low', x: 120, y: 1400, w: 700, h: 200 }, { id: 'right', x: 300, y: 600, w: 700, h: 100 },
    { id: 'top', x: 200, y: 100, w: 400, h: 100 }], '9:16');
  assert.deepEqual(hits.map((h) => `${h.id}:${h.zone}`).sort(), ['low:bottom', 'right:right', 'top:top']);
  assert.equal(hits.find((h) => h.id === 'low').px, 1600 - Math.round(1920 * 0.78));
});

test('browser check report → safe-zone, contrast and lint warnings', () => {
  const report = { format: '9:16', texts: [{ id: 's1', fs: 88, lines: ['a b'], box: { x: 120, y: 1450, w: 600, h: 120 } }], missingFonts: [] };
  const check = {
    lint: { findings: [{ severity: 'warning', code: 'composition_file_too_large' }] },
    runtime: { findings: [{ severity: 'warning', code: 'console_warning', message: `[cut-layout] ${JSON.stringify(report)}` }] },
    contrast: { findings: [{ severity: 'error', text: 'Boka', ratio: 2.1 }] }, layout: { findings: [] },
  };
  assert.equal(layoutReport(check).texts[0].id, 's1');
  const j = judgeCheck(check, '9:16');
  assert.equal(j.safe.length, 1);
  assert.ok(j.warnings.some((w) => w.startsWith('Säker yta: texten i scen s1')));
  assert.ok(j.warnings.some((w) => w.startsWith('Kontrast: 1')));
  assert.ok(!j.warnings.some((w) => w.includes('lint')));
});

// ------------------------------------------------------------------ legibility + look
test('legibility treatment follows the picture under the text', () => {
  assert.equal(legibility({ mean: 0.15, p90: 0.25, p95: 0.3, std: 0.05 }).mode, 'shadow');
  const mid = legibility({ mean: 0.55, p90: 0.7, p95: 0.75, std: 0.1 });
  assert.equal(mid.mode, 'scrim');
  assert.ok(mid.alpha > 0.2 && mid.contrast >= 4.5, JSON.stringify(mid));
  assert.equal(legibility({ mean: 0.9, p90: 0.97, p95: 0.98, std: 0.05 }).mode, 'plate');
  assert.equal(legibility(null).mode, 'scrim');
  const gray = new Uint8Array(10 * 10).fill(51);
  for (let i = 50; i < 100; i++) gray[i] = 204;
  const st = regionStats(gray, 10, 10, { x0: 0, x1: 60, y0: 30, y1: 60 }, 6);
  assert.ok(Math.abs(st.mean - 0.8) < 0.01);
  assert.equal(lookMatrix({ background: '#082f27', accent: '#d6a536' }).split(' ').length, 20);
});

// ------------------------------------------------------------------ sound design
test('synthesized SFX are deterministic, peak-aligned and mixed at their level', () => {
  for (const k of SFX_KINDS) {
    const { data } = synth(k);
    assert.ok(data.length > 100 && Math.max(...data.map(Math.abs)) <= 0.9001, k);
  }
  assert.deepEqual(synth('whoosh', { seed: 3 }).data.slice(0, 50), synth('whoosh', { seed: 3 }).data.slice(0, 50));
  const { L } = mixCues([{ kind: 'impact', t: 1.0 }], 2);
  let at = 0;
  for (let i = 0; i < L.length; i++) if (Math.abs(L[i]) > Math.abs(L[at])) at = i;
  assert.ok(Math.abs(at / SR - 0.98) < 0.01, `peak at ${at / SR}`);
  const peakDb = 20 * Math.log10(Math.abs(L[at]));
  assert.ok(Math.abs(peakDb - (LEVEL_DB.impact + 20 * Math.log10(0.9))) < 0.5, `peak ${peakDb}`);
  // Every sfx native in support.json maps to a synth.
  for (const [native, e] of Object.entries(SUPPORT.effects)) if (e.sfx) assert.ok(SFX_KINDS.includes(e.sfx), native);
});

test('SFX plan: transitions, explicit catalog sounds, riser into the outro', () => {
  const seq = [
    { id: 's1', idx: 0, start: 0, end: 2, winStart: 0, winEnd: 2, textAt: 0.12, natives: ['sfx-riser'], style: 'slam' },
    { id: 's2', idx: 1, start: 2, end: 4, winStart: 1.8, winEnd: 4, textAt: 2.3, natives: ['sfx-pop'], transition: { type: 'whip', d: 0.36 } },
    { id: 's3', idx: 2, start: 4, end: 6, winStart: 4, winEnd: 6, textAt: 4.12, natives: ['sfx-whoosh'], transition: { type: 'push', d: 0.4 } },
  ];
  const cues = planSfx(seq, 6, { outro: true });
  const has = (kind, t) => cues.some((c) => c.kind === kind && Math.abs(c.t - t) < 1e-6);
  assert.ok(has('riser', 2) && has('pop', 2.3) && has('whoosh', 2) && has('whoosh', 4) && has('impact', 0.12) && has('riser', 6));
  assert.equal(cues.filter((c) => c.kind === 'whoosh' && c.t === 4).length, 1); // explicit wins over the automatic one
  assert.ok(!planSfx(seq, 6, { auto: false }).some((c) => c.auto));
});

// ------------------------------------------------------------------ technical QA
test('QA parsers and judgement', () => {
  const black = parseBlack('[blackdetect @ 0x] black_start:0 black_end:0.4 black_duration:0.4\n[blackdetect] black_start:5.1 black_end:5.6 black_duration:0.5');
  assert.deepEqual(black, [{ start: 0, end: 0.4 }, { start: 5.1, end: 5.6 }]);
  const freeze = parseFreeze('lavfi.freezedetect.freeze_start: 2.0\nlavfi.freezedetect.freeze_duration: 1.5\nlavfi.freezedetect.freeze_end: 3.5\nlavfi.freezedetect.freeze_start: 9', 10);
  assert.deepEqual(freeze, [{ start: 2, end: 3.5 }, { start: 9, end: 10 }]);
  const luma = parseLuma('frame:0 pts:0 pts_time:0\nlavfi.signalstats.YAVG=16\nframe:1 pts:1 pts_time:0.033\nlavfi.signalstats.YAVG=120.5');
  assert.deepEqual(luma, [{ t: 0, y: 16 }, { t: 0.033, y: 120.5 }]);
  // 8 opposite swings in one second = strobing; a single flash transition is fine.
  const strobe = Array.from({ length: 30 }, (_, i) => ({ t: i / 30, y: i < 10 ? (i % 2 ? 200 : 40) : 100 }));
  assert.equal(findFlashes(strobe).length, 1);
  const single = Array.from({ length: 30 }, (_, i) => ({ t: i / 30, y: i === 10 ? 230 : 90 }));
  assert.equal(findFlashes(single).length, 0);
  assert.deepEqual(parseSilence('silence_start: 3.2\nsilence_end: 4.5 | silence_duration: 1.3', 10), [{ start: 3.2, end: 4.5 }]);
  const ebu = parseEbur128('Summary:\n\n  Integrated loudness:\n    I:         -16.3 LUFS\n  Loudness range:\n    LRA:         4.2 LU\n  True peak:\n    Peak:       -0.2 dBFS');
  assert.deepEqual(ebu, { I: -16.3, LRA: 4.2, TP: -0.2 });
  assert.equal(parseAstats('Overall\nPeak level dB: -0.000000\nPeak count: 14').peakDb, 0);
  const { warnings, metrics } = judge({ black, freeze, flashes: findFlashes(strobe), loudness: ebu, silence: [{ start: 3.2, end: 4.5 }] },
    { duration: 10, intentDark: [{ start: 0, end: 0.6 }], expectSound: true, targetLufs: -14 });
  const text = warnings.join('\n');
  assert.match(text, /svart bild 5\.1–5\.6/);
  assert.doesNotMatch(text, /svart bild 0–/); // intentional dark-to-light open
  assert.match(text, /stillastående bild 2–3\.5/);
  assert.match(text, /blixtar/);
  assert.match(text, /-16\.3 LUFS/);
  assert.match(text, /dBTP/);
  assert.match(text, /tyst glapp 3\.2–4\.5/);
  assert.equal(metrics.black_s, 0.5);
  assert.deepEqual(judge({ loudness: { I: -14.2, TP: -1.4 }, silence: [] }, { duration: 10, expectSound: true, targetLufs: -14 }).warnings, []);
});
