// One cut: compose the HyperFrames project → lint → render → mix/normalize/encode. Shared by the worker and the CLI.
import { mkdirSync, rmSync } from 'node:fs';
import { join } from 'node:path';

import { compose } from './compose.js';
import { JobError, finish, probe, run } from './finish.js';

export const HYPERFRAMES = `hyperframes@${process.env.HYPERFRAMES_VERSION || '0.8.140'}`;
export const DEFAULT_LIMITS = { master_max_bytes: 80 * 1024 * 1024, preview_max_bytes: Math.floor(9.5 * 1024 * 1024) };

const strip = (s) => s.replace(/\x1b\[[0-9;]*m/g, '');

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
  let composed;
  try {
    composed = compose({ spec, brand, files: sceneFiles, outDir: project, logoId });
  } catch (err) {
    throw new JobError('compose_failed', err.message);
  }
  const warnings = [...composed.warnings];
  if (!skipLint) {
    const result = await lint(project);
    if (result.errors.length) {
      warnings.push(`HyperFrames lint: ${result.errors.length} fel (${result.errors.map((e) => e.code || e.rule || e.message).join(', ')}).`.slice(0, 300));
    }
    log(`lint: ${result.errors.length} errors, ${result.warnings.length} warnings`);
    for (const f of [...result.errors, ...result.warnings]) log(`  ${f.severity} ${f.code || ''} ${f.message || ''}`);
  }
  if (dryRun) return { project, warnings, total: composed.total, config: composed.config };

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
    picture, music: spec.music_asset_id ? described[spec.music_asset_id]?.path : null,
    musicVolume: spec.music_volume ?? 1, duration: composed.total, fps: spec.fps || 30, outDir: workDir,
    previewMax: limits.preview_max_bytes, masterMax: limits.master_max_bytes,
  });
  onStage('uploading', 0.95);
  return {
    master: result.master, preview: result.preview, warnings, project,
    meta: { duration_s: composed.total, loudness_lufs: result.loudness, master_bytes: result.masterBytes,
            preview_bytes: result.previewBytes, hyperframes: HYPERFRAMES },
  };
}
