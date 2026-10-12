// One cut: beats + picture analysis → compose the HyperFrames project → browser check (lint, layout, contrast, safe
// zones) → render → mix (music, SFX, ducking) / normalize / encode → technical QA. Shared by the worker and the CLI.
import { existsSync, mkdirSync, rmSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { beatError, detectBeats } from './beats.js';
import { judgeCheck, parseCheck } from './check.js';
import { FORMATS, compose } from './compose.js';
import { JobError, finish, probe, run } from './finish.js';
import { logoStats, sampleScenes, textBand } from './legibility.js';
import { technicalQa } from './qa.js';

export const HYPERFRAMES = `hyperframes@${process.env.HYPERFRAMES_VERSION || '0.8.140'}`;
const RENDERER_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
export const DEFAULT_LIMITS = { master_max_bytes: 80 * 1024 * 1024, preview_max_bytes: Math.floor(9.5 * 1024 * 1024) };
const flagOff = (name) => ['0', 'false', 'no', 'off'].includes(String(process.env[name] || '').toLowerCase());

const strip = (s) => s.replace(/\x1b\[[0-9;]*m/g, '');
const fmtS = (n) => n.toFixed(2).replace('.', ',');

/** Probe every input so the composition knows durations and which clips carry sound. */
export async function describeFiles(files) {
  const out = {};
  for (const [id, file] of Object.entries(files)) {
    const info = file.kind === 'image' ? { duration: 0, hasAudio: false } : await probe(file.path);
    out[id] = { ...file, duration: info.duration || file.duration || 0, hasAudio: Boolean(info.hasAudio) };
  }
  return out;
}

export async function lint(dir) {
  const { stdout, stderr } = await run('npx', ['--yes', HYPERFRAMES, 'lint', dir, '--json']);
  const text = strip(stdout);
  const start = text.indexOf('{');
  try {
    const data = JSON.parse(text.slice(start));
    const findings = data.findings || data.results || [];
    return {
      errors: findings.filter((f) => f.severity === 'error'),
      warnings: findings.filter((f) => f.severity === 'warning'),
      raw: data,
    };
  } catch {
    return { errors: [], warnings: [], raw: strip(stdout + stderr).slice(-2000) };
  }
}

/** `hyperframes check --json` on the project; null when the browser check cannot run. */
export async function browserCheck(dir) {
  const { stdout } = await run('npx', ['--yes', HYPERFRAMES, 'check', dir, '--json', '--samples', '5'], { timeoutMs: 5 * 60 * 1000 });
  const data = parseCheck(stdout);
  return data && !data.browserSkipped ? data : data && { ...data, runtime: null, contrast: null };
}

/** Where each text scene's words will sit, and which media moments to sample. */
function textScenes(spec, files, format) {
  const fmt = FORMATS[format] || FORMATS['9:16'];
  const room = fmt.H - fmt.safe.top - fmt.safe.bottom;
  return spec.scenes.filter((s) => s.text && files[s.asset_id]).map((s) => {
    const position = s.text_position || (s.purpose === 'hook' || s.purpose === 'cta' ? 'center' : 'bottom');
    const trim = Number(s.trim_start_s || 0);
    const d = Number(s.duration_s);
    return {
      id: s.id, file: files[s.asset_id], at: [trim + d * 0.2, trim + d * 0.5, trim + d * 0.85],
      band: textBand(fmt, position, Math.round(room * (position === 'center' ? 0.55 : 0.34))),
    };
  });
}

/**
 * spec: validated cut spec. files: {assetId: {path, kind}} (scene assets, music, logo).
 * onStage(stage, progress) is called as the work advances. Returns {master, preview, warnings, meta, project}.
 */
export async function renderCut({ spec, brand = {}, files, workDir, logoId = null, limits = DEFAULT_LIMITS,
  onStage = () => {}, skipLint = false, dryRun = false, log = console.log }) {
  mkdirSync(workDir, { recursive: true });
  const project = join(workDir, 'project');
  rmSync(project, { recursive: true, force: true });
  onStage('compose', 0.05);
  const described = await describeFiles(files);
  const sceneFiles = Object.fromEntries(Object.entries(described).filter(([id]) => id !== spec.music_asset_id));
  const musicFile = spec.music_asset_id ? described[spec.music_asset_id] : null;
  const format = FORMATS[spec.format] ? spec.format : '9:16';
  const warnings = [];

  // 1. Beat grid of the music (hyperframes beats, else ffmpeg onsets).
  let beats = null;
  if (musicFile && !flagOff('EDIT_BEAT_SYNC')) {
    beats = await detectBeats(musicFile.path, workDir, Math.max(Number(spec.duration_s || 0), musicFile.duration || 0), { run, hyperframes: HYPERFRAMES, log });
    if (!beats) warnings.push('Beat-synk: ingen tydlig takt i musiken; scenerna behåller sina längder.');
  }
  // 2. Picture analysis under the text (legibility treatment).
  let analysis = null;
  try {
    analysis = await sampleScenes(textScenes(spec, sceneFiles, format), FORMATS[format]);
  } catch (err) {
    log(`legibility: analysen misslyckades (${err.message})`);
  }
  let outro = null;
  if (spec.outro?.file) {
    const path = resolve(RENDERER_ROOT, spec.outro.file);
    if (path.startsWith(RENDERER_ROOT) && existsSync(path)) outro = path;
    else warnings.push(`Slutbilden ${spec.outro.file} saknas i renderaren och hoppades över.`);
  }
  // Automatic SFX need a bed to sit under (music or kept clip sound); alone, loudness normalization would blow them up.
  const keepsSound = spec.scenes.some((s) => s.audio === 'keep' && sceneFiles[s.asset_id]?.hasAudio);
  let logo = null;
  if (logoId && files[logoId]?.path) logo = await logoStats(files[logoId].path).catch(() => null);
  let composed;
  try {
    composed = compose({ spec, brand, files: sceneFiles, outDir: project, logoId, logo, beats, analysis, outro: Boolean(outro),
      autoSfx: !flagOff('EDIT_AUTO_SFX') && (Boolean(musicFile) || keepsSound) });
  } catch (err) {
    throw new JobError('compose_failed', err.message);
  }
  warnings.unshift(...composed.warnings);
  const specTotal = spec.scenes.reduce((s, x) => s + Number(x.duration_s), 0) + (spec.cta ? Number(spec.cta.duration_s || 2.5) : 0);
  const cuts = composed.config.scenes.slice(1).map((s) => s.start);
  let beatMeta = null;
  if (beats) {
    const origCuts = [];
    spec.scenes.slice(0, -1).reduce((acc, s) => { acc += Number(s.duration_s); origCuts.push(acc); return acc; }, 0);
    const moved = composed.timing.snaps.filter((s) => Math.abs(s.delta) > 0.0005);
    beatMeta = {
      source: beats.source, bpm: beats.bpm, period: beats.period, offset: beats.offset, confidence: beats.confidence,
      grid: beats.beats.filter((b) => b.t <= composed.total).map((b) => (b.down ? -b.t : b.t)),
      snaps: composed.timing.snaps, tolerance: composed.timing.tolerance,
      cut_error_before_s: beatError(origCuts, beats), cut_error_after_s: beatError(cuts, beats),
    };
    const maxMove = moved.reduce((m, s) => Math.max(m, Math.abs(s.delta)), 0);
    warnings.push(`Beat-synk: ${beats.bpm} BPM (${beats.source}); ${composed.timing.snaps.length} scengränser på takten`
      + `${moved.length ? ` (${moved.length} flyttade, max ${fmtS(maxMove)} s)` : ''}; längd ${fmtS(specTotal)} → ${fmtS(composed.total)} s.`);
  }

  // 3. Browser check before rendering: lint, runtime, contrast, measured text boxes vs platform safe zones.
  let checkResult = null;
  if (!skipLint) {
    let check = null;
    try {
      check = flagOff('EDIT_HF_CHECK') ? null : await browserCheck(project);
    } catch (err) {
      log(`check: ${err.message}`);
    }
    if (check) {
      checkResult = judgeCheck(check, format);
      warnings.push(...checkResult.warnings);
      log(`check: ${checkResult.lintErrors.length} lint errors, ${checkResult.safe.length} safe-zone hits, ${checkResult.contrast.length} contrast findings`);
      for (const t of checkResult.layout?.texts || []) log(`  text ${t.id}: ${t.fs}px ${JSON.stringify(t.lines)} ${t.legible || ''}`);
    } else {
      const result = await lint(project);
      if (result.errors.length) {
        warnings.push(`HyperFrames lint: ${result.errors.length} fel (${result.errors.map((e) => e.code || e.rule || e.message).join(', ')}).`.slice(0, 300));
      }
      log(`lint: ${result.errors.length} errors, ${result.warnings.length} warnings`);
      for (const f of [...result.errors, ...result.warnings]) log(`  ${f.severity} ${f.code || ''} ${f.message || ''}`);
    }
  }
  const typography = {
    fonts: composed.fonts,
    texts: (checkResult?.layout?.texts || []).map((t) => ({ id: t.id, px: t.fs, lines: t.lines, legible: t.legible })),
  };
  if (dryRun) {
    return { project, warnings, total: composed.total, config: composed.config, sfx: composed.sfx, beats: beatMeta, typography,
      safe: checkResult?.safe || null };
  }

  onStage('rendering', 0.1);
  const picture = join(workDir, 'picture.mp4');
  const args = ['--yes', HYPERFRAMES, 'render', project, '-o', picture, '--crf', '12', '--fps', String(spec.fps || 30)];
  if (process.env.HYPERFRAMES_WORKERS) args.push('--workers', process.env.HYPERFRAMES_WORKERS);
  if (process.env.HYPERFRAMES_RENDER_ARGS) args.push(...process.env.HYPERFRAMES_RENDER_ARGS.split(' ').filter(Boolean));
  let last = 0.1;
  const rendered = await run('npx', args, {
    timeoutMs: 45 * 60 * 1000,
    onLine: (line) => {
      const clean = strip(line).trim();
      const pct = clean.match(/(\d{1,3}(?:\.\d+)?)%/);
      if (pct) {
        const p = 0.1 + Math.min(100, Number(pct[1])) / 100 * 0.7;
        if (p - last >= 0.05) { last = p; onStage('rendering', Number(p.toFixed(2))); }
      }
      if (/error|rendered in|capture ·/i.test(clean)) log(`hyperframes: ${clean}`.slice(0, 400));
    },
  });
  if (rendered.code !== 0) {
    const tail = strip(rendered.stderr || rendered.stdout).split(/\r?\n/).filter(Boolean).slice(-4).join(' | ');
    throw new JobError('render_failed', tail.slice(0, 300), { retryable: true });
  }
  onStage('rendering', 0.85);
  const result = await finish({
    outro, sfx: composed.sfx,
    picture, music: musicFile?.path || null,
    musicVolume: spec.music_volume ?? 1, duration: composed.total, fps: spec.fps || 30, outDir: workDir,
    previewMax: limits.preview_max_bytes, masterMax: limits.master_max_bytes,
  });
  // 4. Technical QA of the cut (the brand outro is checked once, when it is made).
  onStage('qa', 0.9);
  const qa = await technicalQa(result.cut, {
    duration: composed.total, intentDark: composed.intent.dark, targetLufs: -14,
    expectSound: Boolean(musicFile) || keepsSound || composed.sfx.length > 0,
  }, run);
  warnings.push(...qa.warnings);
  onStage('uploading', 0.95);
  return {
    master: result.master, preview: result.preview, warnings: [...new Set(warnings)].slice(0, 40), project,
    meta: {
      duration_s: result.duration ?? composed.total, cut_s: composed.total, outro: outro ? spec.outro.id : null,
      loudness_lufs: result.loudness, master_bytes: result.masterBytes, preview_bytes: result.previewBytes, hyperframes: HYPERFRAMES,
      beats: beatMeta, sfx: composed.sfx.map((c) => `${c.kind}@${c.t}`), typography,
      qa: { ...qa.metrics, safe_zone_hits: checkResult?.safe?.length ?? null, contrast_findings: checkResult?.contrast?.length ?? null },
    },
  };
}
