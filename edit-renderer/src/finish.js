// Audio mix (clip sound + music with ducking), loudness normalization to -14 LUFS, final H.264 master and preview.
import { spawn } from 'node:child_process';
import { statSync } from 'node:fs';
import { join } from 'node:path';

import { mixCues, writeWav } from './sfx.js';

export class JobError extends Error {
  constructor(code, message, { retryable = false } = {}) {
    super(message);
    this.code = code;
    this.retryable = retryable;
  }
}

export function run(cmd, args, { cwd, onLine, timeoutMs = 0 } = {}) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(cmd, args, { cwd, shell: process.platform === 'win32' && cmd === 'npx', windowsHide: true });
    let stdout = '';
    let stderr = '';
    const timer = timeoutMs ? setTimeout(() => child.kill('SIGKILL'), timeoutMs) : null;
    const feed = (chunk, sink) => {
      const text = chunk.toString();
      if (onLine) text.split(/\r?\n|\r/).filter(Boolean).forEach(onLine);
      return sink + text;
    };
    child.stdout.on('data', (c) => { stdout = feed(c, stdout).slice(-200000); });
    child.stderr.on('data', (c) => { stderr = feed(c, stderr).slice(-200000); });
    child.on('error', (err) => { if (timer) clearTimeout(timer); reject(err); });
    child.on('close', (code) => { if (timer) clearTimeout(timer); resolvePromise({ code, stdout, stderr }); });
  });
}

export async function probe(file) {
  const { code, stdout } = await run('ffprobe', ['-v', 'error', '-show_streams', '-show_format', '-of', 'json', file]);
  if (code !== 0) throw new JobError('invalid_output', `ffprobe kunde inte läsa ${file}`);
  const data = JSON.parse(stdout);
  const video = data.streams.find((s) => s.codec_type === 'video');
  const audio = data.streams.find((s) => s.codec_type === 'audio');
  return {
    duration: Number(data.format?.duration || video?.duration || audio?.duration || 0),
    video, audio, hasAudio: Boolean(audio), size: Number(data.format?.size || 0),
  };
}

async function ffmpeg(args, code, what) {
  const result = await run('ffmpeg', ['-hide_banner', '-nostdin', '-y', ...args]);
  if (result.code !== 0) {
    const tail = result.stderr.split(/\r?\n/).filter(Boolean).slice(-3).join(' | ');
    throw new JobError(code, `${what}: ${tail}`.slice(0, 300));
  }
  return result;
}

const LOUDNORM = 'loudnorm=I=-14:TP=-1.5:LRA=11';

async function measure(file) {
  const { stderr } = await run('ffmpeg', ['-hide_banner', '-nostdin', '-i', file, '-vn', '-af', `${LOUDNORM}:print_format=json`, '-f', 'null', '-']);
  const match = stderr.match(/\{[^{}]*"input_i"[^{}]*\}/s);
  if (!match) return null;
  const data = JSON.parse(match[0]);
  const value = Number(data.input_i);
  return Number.isFinite(value) && value > -60 ? data : null;
}

/**
 * picture: HyperFrames render (H.264, maybe with clip sound). music: optional audio file. sfx: optional cue sheet
 * (compose.js planSfx) rendered to one stem and mixed under the music; music + SFX duck under clip sound.
 * Returns {master, cut, preview|null, loudness, masterBytes, previewBytes, sfx}.
 */
export async function finish({ picture, music = null, musicVolume = 1, duration, fps = 30, outDir, previewMax, masterMax,
  outro = null, sfx = null }) {
  const D = Number(duration);
  const pic = await probe(picture);
  const mixFile = join(outDir, 'mix.wav');
  const inputs = ['-i', picture];
  const chains = [];
  let mixLabel = null;
  if (pic.hasAudio) {
    chains.push(`[0:a]aresample=48000,aformat=channel_layouts=stereo,apad,atrim=0:${D},asetpts=PTS-STARTPTS[clip]`);
  }
  let bed = null;
  if (music) {
    inputs.push('-i', music);
    const fadeAt = Math.max(0, D - 1.5).toFixed(3);
    chains.push(`[${inputs.length / 2 - 1}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:${D},asetpts=PTS-STARTPTS,`
      + `volume=${Number(musicVolume).toFixed(3)},afade=t=in:d=0.08,afade=t=out:st=${fadeAt}:d=1.5,apad,atrim=0:${D}[mus]`);
    bed = '[mus]';
  }
  let sfxCount = 0;
  if (sfx && sfx.length) {
    const sfxFile = join(outDir, 'sfx.wav');
    writeWav(sfxFile, mixCues(sfx, D));
    sfxCount = sfx.length;
    inputs.push('-i', sfxFile);
    chains.push(`[${inputs.length / 2 - 1}:a]aresample=48000,aformat=channel_layouts=stereo,apad,atrim=0:${D},asetpts=PTS-STARTPTS[sfx]`);
    if (bed) {
      chains.push(`${bed}[sfx]amix=inputs=2:duration=first:normalize=0[bed]`);
      bed = '[bed]';
    } else {
      bed = '[sfx]';
    }
  }
  if (pic.hasAudio && bed) {
    chains.push('[clip]asplit=2[c1][c2]', `${bed}[c1]sidechaincompress=threshold=0.04:ratio=6:attack=15:release=350[duck]`,
      '[duck][c2]amix=inputs=2:duration=longest:normalize=0[mix]');
    mixLabel = '[mix]';
  } else if (pic.hasAudio) {
    mixLabel = '[clip]';
  } else if (bed) {
    mixLabel = bed;
  }
  let loud = null;
  if (mixLabel) {
    await ffmpeg([...inputs, '-filter_complex', chains.join(';'), '-map', mixLabel, '-c:a', 'pcm_f32le', '-t', String(D), mixFile],
      'audio_failed', 'Ljudmixen misslyckades');
    loud = await measure(mixFile);
  }
  const audioIn = mixLabel ? ['-i', mixFile] : ['-f', 'lavfi', '-t', String(D), '-i', 'anullsrc=r=48000:cl=stereo'];
  const af = loud
    ? `${LOUDNORM}:measured_I=${loud.input_i}:measured_TP=${loud.input_tp}:measured_LRA=${loud.input_lra}`
      + `:measured_thresh=${loud.input_thresh}:offset=${loud.target_offset}:linear=true,aresample=48000`
    : 'anull';
  const capKbps = Math.max(2500, Math.min(14000, Math.floor((masterMax * 0.9 * 8) / D / 1000) - 256));
  const master = join(outDir, 'master.mp4');
  await ffmpeg(['-i', picture, ...audioIn, '-map', '0:v:0', '-map', '1:a:0', '-af', af,
    '-c:v', 'libx264', '-preset', process.env.EDIT_X264_PRESET || 'slow', '-crf', '18', '-maxrate', `${capKbps}k`,
    '-bufsize', `${capKbps * 2}k`, '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-r', String(fps), '-g', String(fps * 2),
    '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2', '-movflags', '+faststart', '-t', String(D), master],
  'render_failed', 'Slutkodningen misslyckades');
  const masterBytes = statSync(master).size;
  if (masterBytes > masterMax) throw new JobError('invalid_output', `Mastern blev ${(masterBytes / 1e6).toFixed(1)} MB (max ${(masterMax / 1e6).toFixed(0)} MB).`);
  const verified = await probe(master);
  if (verified.video?.codec_name !== 'h264' || verified.video?.pix_fmt !== 'yuv420p' || verified.audio?.codec_name !== 'aac'
      || Math.abs(verified.duration - D) > 0.2) {
    throw new JobError('invalid_output', `Mastern klarade inte kontrollen (${verified.video?.codec_name}/${verified.video?.pix_fmt}, ${verified.duration.toFixed(2)} s).`);
  }
  const after = loud ? await measure(master) : null;
  let total = D;
  let final = master;
  let finalBytes = masterBytes;
  if (outro) {
    ({ file: final, duration: total } = await appendOutro({ master, outro, D, fps, outDir, capKbps,
      width: Number(verified.video.width), height: Number(verified.video.height) }));
    finalBytes = statSync(final).size;
    if (finalBytes > masterMax) throw new JobError('invalid_output', `Mastern med slutbild blev ${(finalBytes / 1e6).toFixed(1)} MB.`);
  }
  let preview = null;
  let previewBytes = 0;
  if (finalBytes > previewMax) {
    preview = await makePreview({ master: final, D: total, fps, outDir, previewMax, width: Number(verified.video.width), height: Number(verified.video.height) });
    previewBytes = statSync(preview).size;
  }
  return { master: final, cut: master, preview, masterBytes: finalBytes, previewBytes, duration: total, sfx: sfxCount,
    loudness: after ? Number(Number(after.input_i).toFixed(1)) : null };
}

/**
 * Brand outro (slutbild) after the cut: same size/fps, its own original sound untouched (not re-normalized, so the
 * sonic logo stays identical). Returns {file, duration}.
 */
async function appendOutro({ master, outro, D, fps, outDir, capKbps, width, height }) {
  const info = await probe(outro);
  if (!info.video) throw new JobError('invalid_output', `Slutbilden saknar bild: ${outro}`);
  const O = info.duration;
  const out = join(outDir, 'master-outro.mp4');
  const outroAudio = info.hasAudio
    ? `[1:a]aresample=48000,aformat=channel_layouts=stereo,apad,atrim=0:${O},asetpts=PTS-STARTPTS[a1]`
    : `anullsrc=r=48000:cl=stereo,atrim=0:${O}[a1]`;
  const graph = [
    `[0:v]fps=${fps},scale=${width}:${height},setsar=1,format=yuv420p[v0]`,
    `[1:v]fps=${fps},scale=${width}:${height}:force_original_aspect_ratio=decrease,pad=${width}:${height}:(ow-iw)/2:(oh-ih)/2:color=0x0e1f15,setsar=1,format=yuv420p[v1]`,
    '[0:a]aresample=48000,aformat=channel_layouts=stereo[a0]',
    outroAudio,
    '[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]',
  ];
  await ffmpeg(['-i', master, '-i', outro, '-filter_complex', graph.join(';'), '-map', '[v]', '-map', '[a]',
    '-c:v', 'libx264', '-preset', process.env.EDIT_X264_PRESET || 'slow', '-crf', '18', '-maxrate', `${capKbps}k`,
    '-bufsize', `${capKbps * 2}k`, '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-r', String(fps), '-g', String(fps * 2),
    '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2', '-movflags', '+faststart', out],
  'render_failed', 'Slutbilden kunde inte läggas till');
  const verified = await probe(out);
  if (Math.abs(verified.duration - (D + O)) > 0.25) {
    throw new JobError('invalid_output', `Videon med slutbild blev ${verified.duration.toFixed(2)} s (väntat ${(D + O).toFixed(2)} s).`);
  }
  return { file: out, duration: D + O };
}

async function makePreview({ master, D, fps, outDir, previewMax, width, height }) {
  const out = join(outDir, 'preview.mp4');
  const log = join(outDir, 'x264pass');
  let factor = 0.93;
  for (let attempt = 0; attempt < 3; attempt++) {
    const totalKbps = Math.floor((previewMax * 8 * factor) / D / 1000);
    const videoKbps = Math.max(300, totalKbps - 96);
    // Below ~2 Mbit/s a 720p picture looks better than a starved 1080p one.
    const scale = videoKbps < 2200 ? (width <= height ? 'scale=720:-2' : 'scale=-2:720') : 'null';
    const common = ['-i', master, '-vf', scale, '-c:v', 'libx264', '-preset', 'medium', '-b:v', `${videoKbps}k`,
      '-maxrate', `${Math.floor(videoKbps * 1.4)}k`, '-bufsize', `${videoKbps * 2}k`, '-pix_fmt', 'yuv420p', '-r', String(fps),
      '-passlogfile', log];
    await ffmpeg([...common, '-pass', '1', '-an', '-f', 'mp4', process.platform === 'win32' ? 'NUL' : '/dev/null'],
      'render_failed', 'Förhandsvisningen (pass 1) misslyckades');
    await ffmpeg([...common, '-pass', '2', '-c:a', 'aac', '-b:a', '96k', '-ar', '48000', '-ac', '2', '-movflags', '+faststart', out],
      'render_failed', 'Förhandsvisningen (pass 2) misslyckades');
    if (statSync(out).size <= previewMax) return out;
    factor *= 0.85;
  }
  throw new JobError('invalid_output', 'Förhandsvisningen blev större än 9,5 MB.');
}
