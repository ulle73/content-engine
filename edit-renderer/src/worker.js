#!/usr/bin/env node
// Cloud edit worker (GitHub Actions): claim queued cut jobs from content-engine, render them, upload, exit.
//   CONTENT_APP_URL            default https://content-engine-mcp.onrender.com
//   CONTENT_EDIT_WORKER_TOKEN  same value as EDIT_WORKER_TOKEN on the server (≥ 32 characters)
//   EDIT_JOB_ID                optional: claim this job first (workflow_dispatch input)
//   EDIT_MAX_JOBS              jobs per run (default 3)
import { createHash, randomUUID } from 'node:crypto';
import { mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { JobError } from './finish.js';
import { renderCut } from './render.js';

const APP = (process.env.CONTENT_APP_URL || 'https://content-engine-mcp.onrender.com').replace(/\/+$/, '');
const TOKEN = process.env.CONTENT_EDIT_WORKER_TOKEN || process.env.EDIT_WORKER_TOKEN || '';
const MAX_JOBS = Math.max(1, Number(process.env.EDIT_MAX_JOBS || 3));
const WORK = process.env.EDIT_WORK_DIR || join(tmpdir(), 'edit-render');
const WORKER_ID = randomUUID();
const EXT = { 'video/mp4': '.mp4', 'image/jpeg': '.jpg', 'image/png': '.png', 'image/webp': '.webp', 'audio/wav': '.wav',
  'audio/mpeg': '.mp3', 'audio/mp4': '.m4a' };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const log = (...args) => console.log(new Date().toISOString().slice(11, 19), ...args);

class HttpError extends Error {
  constructor(status, body) {
    super(`HTTP ${status}: ${String(body).slice(0, 200)}`);
    this.status = status;
  }
}

async function api(path, { method = 'POST', json, form, headers = {}, timeoutMs = 60000 } = {}) {
  const init = { method, headers: { Authorization: `Bearer ${TOKEN}`, ...headers }, signal: AbortSignal.timeout(timeoutMs) };
  if (json !== undefined) {
    init.body = JSON.stringify(json);
    init.headers['Content-Type'] = 'application/json';
  } else if (form) {
    init.body = form;
  }
  const response = await fetch(`${APP}/internal/edit/${path}`, init);
  const text = await response.text();
  if (!response.ok) throw new HttpError(response.status, text);
  return text ? JSON.parse(text) : {};
}

/** Render's free plan sleeps: keep trying for ~2 minutes before giving up. */
async function claim(jobId) {
  const delays = [0, 5, 10, 15, 20, 25, 30, 30];
  let lastError = null;
  for (const delay of delays) {
    if (delay) await sleep(delay * 1000);
    try {
      const data = await api('claim/', { json: { worker_id: WORKER_ID, job_id: jobId || null }, timeoutMs: 90000 });
      return data.job || null;
    } catch (err) {
      if (err instanceof HttpError && err.status === 401) throw new Error('Workertoken avvisades (EDIT_WORKER_TOKEN/CONTENT_EDIT_WORKER_TOKEN).');
      if (err instanceof HttpError && err.status < 500 && err.status !== 429) throw err;
      lastError = err;
      log(`claim: appen svarar inte än (${err.message}); försöker igen`);
    }
  }
  throw new Error(`Kunde inte nå ${APP}: ${lastError?.message}`);
}

async function download(job, asset, dir) {
  const target = join(dir, `${asset.id}${EXT[asset.mime_type] || ''}`);
  const sources = [asset.download_url, asset.url].filter(Boolean);
  for (const source of sources) {
    try {
      const own = source === asset.url;
      const response = await fetch(source, {
        headers: own ? { Authorization: `Bearer ${TOKEN}`, 'X-Edit-Lease': job.lease } : {},
        signal: AbortSignal.timeout(5 * 60 * 1000),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = Buffer.from(await response.arrayBuffer());
      if (asset.sha256 && createHash('sha256').update(data).digest('hex') !== asset.sha256) throw new Error('fel kontrollsumma');
      writeFileSync(target, data);
      return target;
    } catch (err) {
      log(`nedladdning av ${asset.id} via ${source === asset.url ? 'appen' : 'R2'} misslyckades: ${err.message}`);
    }
  }
  throw new JobError('asset_missing', `Filen ${asset.id} kunde inte hämtas.`, { retryable: true });
}

async function processJob(job) {
  const dir = join(WORK, job.job_id);
  rmSync(dir, { recursive: true, force: true });
  mkdirSync(join(dir, 'inputs'), { recursive: true });
  let progress = 0;
  let stage = 'claimed';
  const beat = async () => {
    try {
      await api('heartbeat/', { json: { job_id: job.job_id, lease: job.lease, progress, stage } });
    } catch (err) {
      log(`heartbeat misslyckades: ${err.message}`);
    }
  };
  const timer = setInterval(beat, (job.limits?.heartbeat_s || 30) * 1000);
  try {
    log(`jobb ${job.job_id}: "${job.spec.title}" (${job.spec.duration_s} s, ${job.spec.format}), försök ${job.attempt}`);
    const files = {};
    for (const asset of job.assets) {
      files[asset.id] = { kind: asset.kind, path: await download(job, asset, join(dir, 'inputs')) };
    }
    const result = await renderCut({
      spec: job.spec, brand: job.brand, files, workDir: dir, logoId: job.brand?.logo_asset_id || null, limits: job.limits,
      onStage: (s, p) => {
        const changed = s !== stage;
        stage = s;
        progress = p;
        if (changed) beat();
      },
      log,
    });
    const form = new FormData();
    form.append('file', new Blob([readFileSync(result.master)], { type: 'video/mp4' }), 'master.mp4');
    if (result.preview) form.append('preview', new Blob([readFileSync(result.preview)], { type: 'video/mp4' }), 'preview.mp4');
    form.append('warnings', JSON.stringify(result.warnings));
    form.append('meta', JSON.stringify(result.meta));
    stage = 'uploading';
    const done = await api(`output/${job.job_id}/`, { form, headers: { 'X-Edit-Lease': job.lease }, timeoutMs: 15 * 60 * 1000 });
    log(`klart: ${JSON.stringify({ status: done.job?.status, review: done.job?.review_id, discord: done.job?.discord_posted, ...result.meta })}`);
    for (const w of result.warnings) log(`varning: ${w}`);
    return true;
  } catch (err) {
    const code = err instanceof JobError ? err.code : err instanceof HttpError ? 'upload_failed' : 'render_failed';
    log(`jobb ${job.job_id} misslyckades: ${code}: ${err.message}`);
    try {
      await api('failed/', { json: { job_id: job.job_id, lease: job.lease, code, detail: String(err.message || '').slice(0, 300),
        retryable: Boolean(err.retryable) } });
    } catch (reportErr) {
      log(`kunde inte rapportera felet: ${reportErr.message}`);
    }
    return false;
  } finally {
    clearInterval(timer);
    if (!process.env.EDIT_KEEP_WORK) rmSync(dir, { recursive: true, force: true });
  }
}

async function main() {
  if (TOKEN.length < 32) throw new Error('CONTENT_EDIT_WORKER_TOKEN saknas eller är kortare än 32 tecken.');
  let failures = 0;
  let handled = 0;
  for (let i = 0; i < MAX_JOBS; i++) {
    const job = await claim(i === 0 ? process.env.EDIT_JOB_ID : null);
    if (!job) break;
    handled++;
    if (!(await processJob(job))) failures++;
  }
  log(handled ? `${handled} jobb körda, ${failures} misslyckades.` : 'Inga klippjobb i kö.');
  process.exit(failures ? 1 : 0);
}

main().catch((err) => {
  console.error(err.message || err);
  process.exit(1);
});
