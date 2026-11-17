#!/usr/bin/env node
/**
 * Renderar SMS-filmer som beställts i dashboarden (Generera video → SMS-film).
 *
 * Körs i GitHub Actions (.github/workflows/sms-film-render.yml). Hämtar ett jobb från Content Engine
 * (/internal/sms-film/), bygger konversationen med build.mjs i en egen arbetsmapp, renderar med HyperFrames
 * och laddar upp MP4:an. Apple-filerna (typsnitt, emoji, ljud, iPhone-ramen) är privata: de hämtas från
 * dashboarden per jobb, packas upp i IMESSAGE_CACHE och checkas aldrig in eller cachas i Actions.
 *
 * Miljö: CONTENT_APP_URL, CONTENT_EDIT_WORKER_TOKEN (eller EDIT_WORKER_TOKEN), SMS_FILM_JOB_ID (valfritt),
 * SMS_FILM_MAX_JOBS (standard 3), HYPERFRAMES_VERSION, HYPERFRAMES_WORKERS, HYPERFRAMES_RENDER_ARGS.
 */
import {spawn} from 'node:child_process';
import {createHash, randomUUID} from 'node:crypto';
import {cp, mkdir, mkdtemp, readFile, rm, stat, writeFile} from 'node:fs/promises';
import {tmpdir, homedir} from 'node:os';
import {dirname, join, resolve, sep} from 'node:path';
import {fileURLToPath} from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(HERE, '..', '..', '..');
const OUTRO_SRC = join(REPO, 'edit-renderer', 'outros', 'golfkuponger', 'spotlight-9x16.mp4');
const SLUTMALL_RENDER = join(REPO, 'library', 'templates', 'golfkuponger-slutmallar', 'render.mjs');
const APP = (process.env.CONTENT_APP_URL || 'https://content-engine-mcp.onrender.com').replace(/\/+$/, '');
const TOKEN = process.env.CONTENT_EDIT_WORKER_TOKEN || process.env.EDIT_WORKER_TOKEN || '';
const MAX_JOBS = Math.max(1, Number(process.env.SMS_FILM_MAX_JOBS || 3));
const HYPERFRAMES = `hyperframes@${process.env.HYPERFRAMES_VERSION || '0.9.39'}`;
const CACHE = process.env.IMESSAGE_CACHE || join(homedir(), '.cache', 'imessage-mall');
const WORKER_ID = `gh-${randomUUID()}`;
// Kopieras inte in i arbetsmappen: genererat, tungt eller privat.
const SKIP = new Set(['node_modules', '.hyperframes', 'out', 'preview.mp4', 'conversation.generated.js']);
const SKIP_ASSETS = new Set(['fonts', 'ljud', 'outro', 'upload', 'iphone-17.png']);

export class JobError extends Error {
  constructor(code, message, {retryable = false} = {}) {
    super(message);
    this.code = code;
    this.retryable = retryable;
  }
}

class HttpError extends Error {
  constructor(status, body) {
    super(`HTTP ${status}: ${String(body?.error || body || '').slice(0, 200)}`);
    this.status = status;
  }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function api(path, {method = 'POST', json, form, headers = {}, timeoutMs = 60_000} = {}) {
  const init = {method, headers: {Authorization: `Bearer ${TOKEN}`, ...headers}, signal: AbortSignal.timeout(timeoutMs)};
  if (json !== undefined) {
    init.headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(json);
  } else if (form) {
    init.body = form;
  }
  const res = await fetch(`${APP}/internal/sms-film/${path}`, init);
  const text = await res.text();
  let body;
  try { body = text ? JSON.parse(text) : {}; } catch { body = text; }
  if (!res.ok) throw new HttpError(res.status, body);
  return body;
}

/** Hämtar ett jobb. Render sover ibland: försök igen en stund innan vi ger upp. */
async function claim(jobId) {
  const delays = [0, 5, 10, 15, 20, 25, 30, 30];
  let last;
  for (const d of delays) {
    if (d) await sleep(d * 1000);
    try {
      const body = await api('claim/', {json: {worker_id: WORKER_ID, ...(jobId ? {job_id: jobId} : {})}});
      return body; // {job} eller {job: null, skipped} när en bild saknas (servern har redan markerat jobbet)
    } catch (err) {
      last = err;
      if (err instanceof HttpError && err.status === 401) throw new Error('Content Engine nekade token (401). Kontrollera CONTENT_EDIT_WORKER_TOKEN.');
      if (err instanceof HttpError && err.status >= 400 && err.status < 500 && err.status !== 429) throw err;
    }
  }
  throw last;
}

/** Laddar ner en fil (lease krävs) och kontrollerar sha256 om den finns. */
async function download(url, dest, lease, sha256) {
  let res;
  try {
    res = await fetch(url, {headers: {Authorization: `Bearer ${TOKEN}`, 'X-Edit-Lease': lease}, signal: AbortSignal.timeout(300_000)});
  } catch (err) {
    throw new JobError('asset_missing', `nedladdning misslyckades (${err.name})`, {retryable: true});
  }
  if (!res.ok) throw new JobError('asset_missing', `nedladdning gav HTTP ${res.status}`, {retryable: res.status >= 500});
  const buf = Buffer.from(await res.arrayBuffer());
  if (sha256 && createHash('sha256').update(buf).digest('hex') !== sha256) {
    throw new JobError('asset_missing', 'en nedladdad bild matchar inte sin kontrollsumma', {retryable: true});
  }
  await mkdir(dirname(dest), {recursive: true});
  await writeFile(dest, buf);
  return buf.length;
}

/** Kör ett kommando utan skal. Skriver bara slutet av utskriften vid fel (inga hemligheter i argumenten). */
function run(cmd, args, {cwd, env, onLine, timeoutMs = 45 * 60_000} = {}) {
  return new Promise((resolveRun, reject) => {
    const child = spawn(cmd, args, {cwd, env: {...process.env, ...env}, shell: process.platform === 'win32'});
    let tail = '';
    const take = (chunk) => {
      const s = chunk.toString();
      tail = (tail + s).slice(-4000);
      if (onLine) for (const line of s.split(/\r?\n|\r/)) if (line.trim()) onLine(line);
    };
    child.stdout.on('data', take);
    child.stderr.on('data', take);
    const timer = setTimeout(() => child.kill('SIGKILL'), timeoutMs);
    child.on('error', (err) => { clearTimeout(timer); reject(err); });
    child.on('close', (code) => {
      clearTimeout(timer);
      if (code === 0) resolveRun(tail);
      else reject(Object.assign(new Error(`${cmd} ${args[0] || ''} avslutades med ${code}`), {tail}));
    });
  });
}

/** Säkerställer att en sökväg från servern stannar i arbetsmappen. */
export function safeJoin(root, rel) {
  if (typeof rel !== 'string' || !/^assets\/upload\/[0-9a-f-]{36}\.[a-z0-9]{2,5}$/.test(rel)) {
    throw new JobError('asset_missing', `ogiltig bildsökväg ${String(rel).slice(0, 80)}`);
  }
  const full = resolve(root, rel);
  if (!full.startsWith(resolve(root) + sep)) throw new JobError('asset_missing', 'bildsökväg utanför arbetsmappen');
  return full;
}

/** Kopierar mallen till en egen mapp så att jobb aldrig delar genererade filer. */
export async function prepareWorkdir(root) {
  await cp(HERE, root, {
    recursive: true,
    filter: (src) => {
      const rel = src.slice(HERE.length + 1).split(sep);
      if (!rel[0]) return true;
      if (SKIP.has(rel[0])) return false;
      if (rel[0] === 'assets' && rel[1] && SKIP_ASSETS.has(rel[1])) return false;
      return true;
    },
  });
  await mkdir(join(root, 'assets', 'outro'), {recursive: true});
  // build.mjs letar efter slutbilden uppåt från mallen; i en tillfällig mapp hittar den inte repot.
  await cp(OUTRO_SRC, join(root, 'assets', 'outro', 'spotlight-9x16.mp4'));
}

async function applePack(payload) {
  const archive = join(tmpdir(), `imessage-pack-${payload.job_id}.tar.gz`);
  try {
    await download(payload.apple_pack_url, archive, payload.lease, null);
    await mkdir(CACHE, {recursive: true});
    await run('tar', ['-xzf', archive, '-C', CACHE]).catch((err) => {
      throw new JobError('asset_missing', `Apple-paketet gick inte att packa upp (${err.message})`);
    });
  } finally {
    await rm(archive, {force: true});
  }
}

async function probeDuration(file) {
  const out = await run('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', file]);
  const s = Number(out.trim().split(/\s+/).pop());
  return Number.isFinite(s) ? Math.round(s * 100) / 100 : null;
}

/** SMS-film: kopiera mallen, hämta Apple-filer och bilder, bygg och rendera med HyperFrames. Ger sökvägen till MP4:an. */
async function buildSmsFilm(payload, work, setStage, setProgress) {
  const {job_id: id, lease} = payload;
  console.log(`[${id}] förbereder (${(payload.assets || []).length} bilder, försök ${payload.attempt})`);
  await prepareWorkdir(work);
  if (!process.env.IMESSAGE_SKIP_APPLE) await applePack(payload);
  for (const asset of payload.assets || []) await download(asset.url, safeJoin(work, asset.path), lease, asset.sha256);
  // En egen slutmall som filmen slutar med (renderad tidigare i Content Engine).
  if (payload.outro_asset) {
    const o = payload.outro_asset;
    if (typeof o.path !== 'string' || !/^assets\/outro\/slutmall-[0-9a-f-]{36}\.mp4$/.test(o.path)) {
      throw new JobError('asset_missing', `ogiltig sökväg för slutmallen ${String(o.path).slice(0, 80)}`);
    }
    await download(o.url, join(work, o.path), lease, o.sha256);
  }
  await writeFile(join(work, 'conversation.json'), JSON.stringify(payload.conversation, null, 2));

  await setStage('building', 0.1);
  await run(process.execPath, ['build.mjs'], {cwd: work, env: {IMESSAGE_CACHE: CACHE}}).catch((err) => {
    throw new JobError('build_failed', (err.tail || err.message).split('\n').filter(Boolean).slice(-3).join(' | '));
  });
  await run('npx', ['--yes', HYPERFRAMES, 'check'], {cwd: work}).catch((err) => {
    throw new JobError('build_failed', `hyperframes check: ${(err.tail || err.message).slice(-250)}`);
  });

  await setStage('rendering', 0.15);
  const out = join(work, 'out', 'film.mp4');
  const args = ['--yes', HYPERFRAMES, 'render', '--quality', 'looks', '-o', out];
  if (process.env.HYPERFRAMES_WORKERS) args.push('--workers', process.env.HYPERFRAMES_WORKERS);
  if (process.env.HYPERFRAMES_RENDER_ARGS) args.push(...process.env.HYPERFRAMES_RENDER_ARGS.split(' ').filter(Boolean));
  await run('npx', args, {
    cwd: work,
    onLine: (line) => {
      const m = line.match(/(\d{1,3}(?:\.\d+)?)\s*%/);
      if (m) setProgress(0.15 + 0.75 * Math.min(100, Number(m[1])) / 100);
    },
  }).catch((err) => { throw new JobError('render_failed', (err.tail || err.message).slice(-250), {retryable: true}); });
  return out;
}

async function processJob(payload) {
  const {job_id: id, lease, limits = {}} = payload;
  const work = await mkdtemp(join(tmpdir(), `sms-film-${id.slice(0, 8)}-`));
  let progress = 0.02, stage = 'preparing';
  const beat = async () => {
    try {
      await api('heartbeat/', {json: {job_id: id, lease, progress: Math.min(0.99, progress), stage}, timeoutMs: 20_000});
    } catch (err) {
      console.warn(`[${id}] heartbeat misslyckades: ${err.message}`);
    }
  };
  const timer = setInterval(beat, Math.max(10, limits.heartbeat_s || 30) * 1000);
  const warnings = [];
  try {
    await beat();
    let out;
    if (payload.kind === 'slutmall') {
      // Slutmall: svingloggan + två textrader, renderad av golfkuponger-slutmallar/render.mjs (Playwright + ffmpeg).
      // Inga Apple-filer och inga bilder behövs.
      const {mall, rad1 = '', rad2, effekt = 'small', stil = {}} = payload.slutmall || {};
      const format = payload.slutmall?.format === '4x5' ? '4x5' : '9x16';
      console.log(`[${id}] slutmall ${mall}, ${format}, effekt ${effekt} (försök ${payload.attempt})`);
      const jobbPath = join(work, 'jobb.json');
      await writeFile(jobbPath, JSON.stringify({mall, rad1, rad2, effekt, stil, ut: work, format: [format]}));
      stage = 'rendering'; progress = 0.1; await beat();
      const tail = await run(process.execPath, [SLUTMALL_RENDER, '--json', jobbPath], {cwd: REPO, timeoutMs: 20 * 60_000})
        .catch((err) => { throw new JobError('render_failed', (err.tail || err.message).slice(-250), {retryable: true}); });
      const line = tail.split(/\r?\n/).reverse().find((l) => l.trim().startsWith('{'));
      try { out = JSON.parse(line).filer[0].fil; } catch { throw new JobError('invalid_output', 'slutmallen gav inget filnamn'); }
    } else {
      out = await buildSmsFilm(payload, work, async (s, p) => { stage = s; progress = p; await beat(); }, (p) => { progress = Math.max(progress, p); });
    }

    stage = 'checking'; progress = 0.92; await beat();
    const size = (await stat(out).catch(() => ({size: 0}))).size;
    if (!size) throw new JobError('invalid_output', 'ingen MP4 skapades');
    if (limits.output_max_bytes && size > limits.output_max_bytes) throw new JobError('invalid_output', `filen är ${Math.round(size / 1e6)} MB`);
    await run('ffmpeg', ['-v', 'error', '-i', out, '-f', 'null', '-']).catch((err) => {
      throw new JobError('invalid_output', `videon går inte att avkoda: ${(err.tail || '').slice(-200)}`);
    });
    const duration = await probeDuration(out).catch(() => null);
    if (!duration) warnings.push('Längden kunde inte läsas ur videon.');

    stage = 'uploading'; progress = 0.95; await beat();
    const form = new FormData();
    form.append('file', new Blob([await readFile(out)], {type: 'video/mp4'}), payload.kind === 'slutmall' ? 'slutmall.mp4' : 'film.mp4');
    form.append('warnings', JSON.stringify(warnings));
    form.append('meta', JSON.stringify({duration_s: duration}));
    await api(`output/${id}/`, {form, headers: {'X-Edit-Lease': lease}, timeoutMs: 15 * 60_000});
    console.log(`[${id}] klar: ${Math.round(size / 1e5) / 10} MB, ${duration} s`);
    return true;
  } catch (err) {
    const code = err instanceof JobError ? err.code : err instanceof HttpError ? 'upload_failed' : 'render_failed';
    const retryable = err instanceof JobError ? err.retryable : true;
    const detail = String(err.message || err).slice(0, 300);
    console.error(`[${id}] misslyckades (${code}): ${detail}`);
    try {
      await api('failed/', {json: {job_id: id, lease, code, detail, retryable}, timeoutMs: 20_000});
    } catch (reportErr) {
      console.error(`[${id}] kunde inte rapportera felet: ${reportErr.message}`);
    }
    return false;
  } finally {
    clearInterval(timer);
    await rm(work, {recursive: true, force: true});
  }
}

async function main() {
  if (TOKEN.length < 32) {
    console.error('CONTENT_EDIT_WORKER_TOKEN saknas eller är för kort (minst 32 tecken).');
    process.exit(1);
  }
  let failed = 0, done = 0;
  for (let i = 0; i < MAX_JOBS; i++) {
    const {job, skipped} = await claim(i === 0 ? process.env.SMS_FILM_JOB_ID : undefined);
    if (skipped) { console.log('Hoppade över ett jobb vars bilder saknas.'); failed++; continue; }
    if (!job) break;
    if (await processJob(job)) done++; else failed++;
  }
  console.log(`SMS-filmer: ${done} klara, ${failed} misslyckade.`);
  if (failed) process.exit(1);
}

if (resolve(process.argv[1] || '') === fileURLToPath(import.meta.url)) {
  main().catch((err) => {
    console.error(`Stopp: ${err.message}`);
    process.exit(1);
  });
}
