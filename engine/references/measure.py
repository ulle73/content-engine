"""Exact, free measurements of a reference video with PyAV (the ffmpeg libraries; Render has no ffmpeg binary).

- cuts: hard cuts from colour-histogram jumps between consecutive frames (frame accurate), plus soft transitions
  (flash, fade, dissolve) where the picture is stable, changes over a few frames and is stable again
- scenes: start/end between cuts, with how much the picture moves (camera or subject motion)
- audio: loudness envelope, silence, a tempo estimate and how many cuts land on the beat
- proxy: a small H.264/AAC copy (≤ 720 px) that the vision model watches; cheaper and under upload limits
- sheet: one frame per scene with its time, for people and chat models to look at

The vision model gets these numbers so its breakdown can use exact times instead of guessing them.
"""

from __future__ import annotations

import io
import math
from fractions import Fraction

import av
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ANALYSIS_W = 64
MIN_SCENE_S = 0.3
PROXY_LONG_SIDE = 720
MAX_SHEET_FRAMES = 24
AUDIO_RATE = 16000


class MeasureError(ValueError):
    pass


def _open(data: bytes):
    try:
        return av.open(io.BytesIO(data))
    except (av.error.FFmpegError, OSError) as exc:
        raise MeasureError("Filen kunde inte läsas som video.") from exc


def probe(data: bytes) -> dict:
    with _open(data) as container:
        if not container.streams.video:
            raise MeasureError("Filen innehåller ingen video.")
        stream = container.streams.video[0]
        duration = (container.duration / av.time_base) if container.duration else (
            float(stream.duration * stream.time_base) if stream.duration else 0.0)
        rate = stream.average_rate or stream.guessed_rate
        return {"duration_s": round(duration, 3), "width": stream.codec_context.width,
                "height": stream.codec_context.height, "fps": round(float(rate), 3) if rate else None,
                "has_audio": bool(container.streams.audio)}


def _histogram(rgb: np.ndarray) -> np.ndarray:
    hist = np.concatenate([np.bincount(rgb[..., c].ravel() >> 4, minlength=16) for c in range(3)]).astype(np.float32)
    return hist / max(hist.sum(), 1.0)


def video_signals(data: bytes) -> tuple[list[float], list[float], list[float], np.ndarray]:
    """Per frame: time, histogram distance to the previous frame (0–2), mean absolute pixel difference (0–1), and the
    colour histogram itself (for transitions that span several frames)."""
    times, hist_d, pix_d, hists = [], [], [], []
    prev_hist = prev_px = None
    with _open(data) as container:
        stream = container.streams.video[0]
        stream.thread_type = "AUTO"
        width = stream.codec_context.width or ANALYSIS_W
        height = stream.codec_context.height or ANALYSIS_W
        size = (ANALYSIS_W, max(2, round(ANALYSIS_W * height / width)))
        for frame in container.decode(stream):
            if frame.time is None:
                continue
            rgb = frame.to_ndarray(width=size[0], height=size[1], format="rgb24")
            hist = _histogram(rgb)
            px = rgb.astype(np.float32) / 255.0
            times.append(float(frame.time))
            hists.append(hist)
            hist_d.append(float(np.abs(hist - prev_hist).sum()) if prev_hist is not None else 0.0)
            pix_d.append(float(np.abs(px - prev_px).mean()) if prev_px is not None else 0.0)
            prev_hist, prev_px = hist, px
    if len(times) < 2:
        raise MeasureError("Videon har för få bildrutor.")
    return times, hist_d, pix_d, np.asarray(hists)


def detect_cuts(times: list[float], hist_d: list[float], pix_d: list[float]) -> list[float]:
    """Hard cuts: a one-frame histogram spike far above the neighbouring frames, with a real pixel change.

    A local test, not a global threshold: a dark shot → black is a small jump (~0.2) but stands out 50× from its
    still neighbours, while handheld footage changes a lot every frame without being cut.
    """
    h = np.asarray(hist_d)
    cuts, last = [], times[0]
    for i in range(1, len(h)):
        neighbours = np.concatenate([h[max(1, i - 6):i], h[i + 1:i + 7]])
        local = float(np.median(neighbours)) if neighbours.size else 0.0
        if h[i] >= max(0.06, 8 * local + 0.03) and pix_d[i] >= 0.02 and times[i] - last >= MIN_SCENE_S:
            cuts.append(round(times[i], 3))
            last = times[i]
    return cuts


def detect_transitions(times: list[float], hists: np.ndarray, cuts: list[float]) -> list[float]:
    """Soft scene changes over several frames (flash, fade, dissolve, whip): the picture is stable before, changes a
    lot across ~0.2–0.4 s, and is stable again after. Not reported within 0.5 s of a hard cut."""
    t = np.asarray(times)
    if t.size < 10:
        return []
    fps = 1.0 / float(np.median(np.diff(t))) if np.median(np.diff(t)) > 0 else 30.0
    found = []
    for span in (0.2, 0.4):
        k, w = max(2, round(span * fps)), max(3, round(0.4 * fps))
        for i in range(k + w, t.size - k - w):
            change = float(np.abs(hists[i + k] - hists[i - k]).sum())
            before = float(np.abs(hists[i - k] - hists[i - k - w]).sum())
            after = float(np.abs(hists[i + k + w] - hists[i + k]).sum())
            if change >= 0.5 and change >= 3 * max(before, after) + 0.1:
                found.append((change, float(t[i])))
    out: list[float] = []
    for change, at in sorted(found, reverse=True):  # strongest first, then suppress neighbours
        if all(abs(at - o) >= 0.6 for o in out) and all(abs(at - c) >= 0.5 for c in cuts):
            out.append(round(at, 3))
    return sorted(out)


def scenes_from(cuts: list[float], duration: float, times: list[float], pix_d: list[float]) -> list[dict]:
    bounds = [0.0, *cuts, duration]
    t_arr, p_arr = np.asarray(times), np.asarray(pix_d)
    scenes = []
    for i, (start, end) in enumerate(zip(bounds, bounds[1:]), start=1):
        if end - start <= 0:
            continue
        inside = (t_arr > start + 0.05) & (t_arr < end - 0.02)
        motion = float(p_arr[inside].mean()) if inside.any() else 0.0
        level = "stilla" if motion < 0.008 else "lugn" if motion < 0.025 else "rörlig" if motion < 0.06 else "mycket rörlig"
        scenes.append({"id": f"s{i}", "start_s": round(start, 2), "end_s": round(end, 2),
                       "duration_s": round(end - start, 2), "motion": round(motion, 4), "motion_level": level})
    return scenes


def audio_signals(data: bytes) -> np.ndarray | None:
    """Mono float32 samples at 16 kHz, or None when there is no sound track."""
    with _open(data) as container:
        if not container.streams.audio:
            return None
        resampler = av.AudioResampler(format="flt", layout="mono", rate=AUDIO_RATE)
        chunks = []
        for frame in container.decode(container.streams.audio[0]):
            for out in resampler.resample(frame):
                chunks.append(out.to_ndarray().reshape(-1))
        for out in resampler.resample(None):
            chunks.append(out.to_ndarray().reshape(-1))
    return np.concatenate(chunks).astype(np.float32) if chunks else None


def _db(value: float) -> float:
    return round(20 * math.log10(max(value, 1e-6)), 1)


def audio_measurements(samples: np.ndarray | None, cuts: list[float]) -> dict:
    if samples is None or samples.size < AUDIO_RATE // 2:
        return {"has_audio": False}
    hop = AUDIO_RATE // 100  # 10 ms
    frames = samples[: samples.size // hop * hop].reshape(-1, hop)
    rms = np.sqrt((frames ** 2).mean(axis=1) + 1e-12)
    db = 20 * np.log10(np.maximum(rms, 1e-6))
    # Silence: at least 0.3 s under -45 dBFS.
    silence, start = [], None
    for i, value in enumerate(np.append(db, 0.0)):
        if value < -45 and start is None:
            start = i
        elif value >= -45 and start is not None:
            if i - start >= 30:
                silence.append([round(start / 100, 2), round(i / 100, 2)])
            start = None
    loud = rms[db > -45]
    result = {
        "has_audio": True,
        "mean_dbfs": _db(float(np.sqrt((loud ** 2).mean()))) if loud.size else _db(0.0),
        "peak_dbfs": _db(float(np.abs(samples).max())),
        "silence": silence[:20],
        "silent_share": round(float((db < -45).mean()), 2),
    }
    # Tempo: autocorrelation of the onset envelope (rise in log energy), 70–180 BPM.
    onset = np.maximum(np.diff(np.log(rms + 1e-6)), 0)
    onset = onset - np.convolve(onset, np.ones(50) / 50, mode="same")
    onset = np.maximum(onset, 0)
    if onset.size > 250 and onset.any():
        acf = np.correlate(onset, onset, mode="full")[onset.size - 1:]
        lags = np.arange(int(6000 / 180), int(6000 / 70) + 1)
        lags = lags[lags < acf.size]
        if lags.size:
            lag = int(lags[np.argmax(acf[lags])])
            confidence = float(acf[lag] / acf[0]) if acf[0] else 0.0
            phase = max(range(lag), key=lambda p: onset[p::lag].sum())
            beats = np.arange(phase, onset.size, lag) / 100.0
            on_beat = [c for c in cuts if beats.size and np.min(np.abs(beats - c)) <= 0.08]
            result.update({"tempo_bpm": round(6000 / lag, 1), "tempo_confidence": round(confidence, 2),
                           "cuts_on_beat": len(on_beat), "cuts_on_beat_share": round(len(on_beat) / len(cuts), 2)
                           if cuts else None})
    return result


def _even(value: float) -> int:
    return max(2, int(round(value / 2)) * 2)


def proxy_and_frames(data: bytes, frame_times: list[float]) -> tuple[bytes, list[tuple[float, Image.Image]]]:
    """Small H.264/AAC copy for the vision model, and RGB frames at the requested times (one decode pass)."""
    wanted = sorted(frame_times)
    grabbed: list[tuple[float, Image.Image]] = []
    out_buf = io.BytesIO()
    with _open(data) as src:
        vin = src.streams.video[0]
        vin.thread_type = "AUTO"
        ain = src.streams.audio[0] if src.streams.audio else None
        w, h = vin.codec_context.width, vin.codec_context.height
        scale = min(1.0, PROXY_LONG_SIDE / max(w, h))
        ow, oh = _even(w * scale), _even(h * scale)
        rate = vin.average_rate or vin.guessed_rate or Fraction(30)
        fps = min(Fraction(rate).limit_denominator(1001), Fraction(30))
        with av.open(out_buf, mode="w", format="mp4") as dst:
            vout = dst.add_stream("libx264", rate=fps)
            vout.width, vout.height, vout.pix_fmt = ow, oh, "yuv420p"
            vout.options = {"crf": "30", "preset": "veryfast", "movflags": "+faststart"}
            aout = resampler = None
            if ain is not None:
                aout = dst.add_stream("aac", rate=44100)
                aout.layout = "mono"
                aout.bit_rate = 64000
                resampler = av.AudioResampler(format="fltp", layout="mono", rate=44100)
            streams = [vin] + ([ain] if ain is not None else [])
            next_t, frame_index = 0.0, 0
            for packet in src.demux(*streams):
                for frame in packet.decode():
                    if isinstance(frame, av.VideoFrame):
                        if frame.time is None:
                            continue
                        while wanted and frame.time >= wanted[0]:
                            grabbed.append((wanted.pop(0), frame.to_image().convert("RGB")))
                        if frame.time + 1e-6 < next_t:
                            continue  # drop frames above 30 fps
                        next_t = frame.time + float(1 / fps)
                        small = frame.reformat(width=ow, height=oh, format="yuv420p")
                        small.pts, small.time_base = frame_index, Fraction(1) / fps
                        frame_index += 1
                        for out in vout.encode(small):
                            dst.mux(out)
                    elif aout is not None:
                        frame.pts = None
                        for res in resampler.resample(frame):
                            for out in aout.encode(res):
                                dst.mux(out)
            for out in vout.encode(None):
                dst.mux(out)
            if aout is not None:
                for out in aout.encode(None):
                    dst.mux(out)
    return out_buf.getvalue(), grabbed


def _font(size: int):
    for name in ("arialbd.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def contact_sheet(frames: list[tuple[str, float, float, Image.Image]], title: str = "") -> bytes:
    """frames: (scene id, start, end, image). Columns of 6 portrait (or 4 landscape) tiles with time labels."""
    if not frames:
        raise MeasureError("Inga bildrutor att visa.")
    portrait = frames[0][3].height >= frames[0][3].width
    cols = 6 if portrait else 4
    tile_w = 220 if portrait else 320
    tile_h = round(tile_w * frames[0][3].height / frames[0][3].width)
    label_h, pad, head = 30, 8, 40 if title else 0
    rows = math.ceil(len(frames) / cols)
    sheet = Image.new("RGB", (cols * (tile_w + pad) + pad, head + rows * (tile_h + label_h + pad) + pad), (18, 18, 18))
    draw = ImageDraw.Draw(sheet)
    if title:
        draw.text((pad, 10), title[:110], fill=(240, 240, 240), font=_font(20))
    font = _font(16)
    for i, (scene_id, start, end, image) in enumerate(frames):
        x = pad + (i % cols) * (tile_w + pad)
        y = head + pad + (i // cols) * (tile_h + label_h + pad)
        sheet.paste(image.resize((tile_w, tile_h)), (x, y))
        draw.text((x + 4, y + tile_h + 5), f"{scene_id}  {start:.2f}–{end:.2f} s", fill=(255, 210, 0), font=font)
    out = io.BytesIO()
    sheet.save(out, format="JPEG", quality=82, optimize=True)
    return out.getvalue()


def measure(data: bytes, title: str = "") -> dict:
    """Everything above in one call: {"probe", "cuts", "scenes", "audio", "proxy" (bytes), "sheet" (bytes)}."""
    info = probe(data)
    times, hist_d, pix_d, hists = video_signals(data)
    duration = info["duration_s"] or times[-1]
    hard = detect_cuts(times, hist_d, pix_d)
    transitions = detect_transitions(times, hists, hard)
    cuts = sorted(hard + transitions)
    scenes = scenes_from(cuts, duration, times, pix_d)
    for scene in scenes[1:]:
        scene["starts_with"] = "övergång" if scene["start_s"] in {round(t, 2) for t in transitions} else "klipp"
    audio = audio_measurements(audio_signals(data) if info["has_audio"] else None, cuts)
    shown = scenes if len(scenes) <= MAX_SHEET_FRAMES else [
        scenes[round(i * (len(scenes) - 1) / (MAX_SHEET_FRAMES - 1))] for i in range(MAX_SHEET_FRAMES)]
    mids = {round((s["start_s"] + s["end_s"]) / 2, 3): s for s in shown}
    proxy, grabbed = proxy_and_frames(data, list(mids))
    by_time = dict(grabbed)
    tiles = [(s["id"], s["start_s"], s["end_s"], by_time[t]) for t, s in mids.items() if t in by_time]
    shot_lengths = [s["duration_s"] for s in scenes]
    summary = {
        "duration_s": round(duration, 2), "scene_count": len(scenes), "cut_count": len(cuts),
        "avg_shot_s": round(sum(shot_lengths) / len(shot_lengths), 2) if shot_lengths else None,
        "first_cut_s": cuts[0] if cuts else None,
        "cuts_first_3s": sum(1 for c in cuts if c <= 3.0),
    }
    summary["transitions"] = len(transitions)
    return {"probe": info, "summary": summary, "cuts": cuts, "transitions": transitions, "scenes": scenes,
            "audio": audio,
            "proxy": proxy, "sheet": contact_sheet(tiles, title) if tiles else b""}
