"""Technical shot scoring: find the best window of a clip and compare clips, without any paid service.

The best editors never use a whole stock clip; they take its best second or two. This samples a clip at a few frames
per second (small grayscale frames via PyAV) and scores every window of the wanted length on:
  sharpness  – variance of a Laplacian (blurry, soft or out-of-focus frames score low),
  exposure   – mean luma near mid-grey (crushed or blown-out frames score low; skipped for intentionally dark shots),
  motion     – a little movement reads as film, none reads as a still, a lot reads as shake,
  cuts       – a hard cut inside the window (stock clips often contain several shots) is penalised.
Scores are 0–10 and comparable between clips. analyze() never raises on a bad file; it returns {} instead.
"""

from __future__ import annotations

import io
import logging

import numpy as np

log = logging.getLogger(__name__)

SAMPLE_FPS = 4.0
WIDTH = 160
MAX_SECONDS = 40.0
CUT_DIFF = 0.12  # a hard cut: luma difference this large AND CUT_RATIO × the motion around it


def _laplacian_var(gray: np.ndarray) -> float:
    lap = (-4 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1] + gray[1:-1, :-2] + gray[1:-1, 2:])
    return float(lap.var())


def analyze(data: bytes, *, sample_fps: float = SAMPLE_FPS, max_seconds: float = MAX_SECONDS) -> dict:
    """{"duration", "t", "sharp", "luma", "motion"} sampled over the clip, or {} when it cannot be decoded."""
    import av

    times, sharp, luma, motion = [], [], [], []
    prev = None
    try:
        with av.open(io.BytesIO(data)) as container:
            stream = container.streams.video[0]
            stream.thread_type = "AUTO"
            duration = float(stream.duration * stream.time_base) if stream.duration else \
                float(container.duration or 0) / 1_000_000
            step, next_t = 1.0 / sample_fps, 0.0
            for frame in container.decode(stream):
                t = float(frame.time or 0)
                if t > max_seconds:
                    break
                if t + 1e-6 < next_t:
                    continue
                next_t = t + step
                height = max(2, round(frame.height * WIDTH / max(frame.width, 1)))
                gray = frame.reformat(width=WIDTH, height=height, format="gray").to_ndarray().astype(np.float32) / 255
                times.append(round(t, 3))
                sharp.append(_laplacian_var(gray) * 1000)
                luma.append(float(gray.mean()))
                motion.append(float(np.abs(gray - prev).mean()) if prev is not None else 0.0)
                prev = gray
    except Exception as exc:  # noqa: BLE001 - any undecodable file just has no analysis
        log.info("Shot analysis failed: %s", exc)
        return {}
    if not times:
        return {}
    if len(motion) > 1:
        motion[0] = motion[1]
    return {"duration": max(duration, times[-1]), "t": times, "sharp": sharp, "luma": luma, "motion": motion}


def _sample_scores(analysis: dict, *, dark_ok: bool) -> list[float]:
    # Calibrated on real 1080p footage at WIDTH px: sharp ≈ 5–10 (gaussian blur σ4 ≈ 0.5), motion ≈ 0.01–0.10 for
    # handheld/slow camera moves, 0 for a frozen frame, > 0.12 for shake or whip movement.
    out = []
    for sharp, luma, move in zip(analysis["sharp"], analysis["luma"], analysis["motion"]):
        s_sharp = min(1.0, sharp / 4.0)
        s_expo = 1.0 if dark_ok else max(0.0, 1.0 - max(0.0, abs(luma - 0.45) - 0.12) * 4)
        if move < 0.004:
            s_move = 0.0  # frozen: reads as a still image
        elif move < 0.01:
            s_move = 0.6
        elif move <= 0.10:
            s_move = 1.0
        else:
            s_move = max(0.3, 1.0 - (move - 0.10) * 5)
        out.append(0.4 * s_sharp + 0.3 * s_expo + 0.3 * s_move)
    return out


CUT_RATIO = 3.0


def cuts(analysis: dict) -> list[int]:
    """Indexes of samples that start a new shot (a spike in difference, not just fast movement)."""
    motion = analysis.get("motion") or []
    out = []
    for j in range(1, len(motion)):
        around = sorted(motion[max(1, j - 2):j] + motion[j + 1:j + 3])
        base = around[len(around) // 2] if around else 0.0
        if motion[j] > CUT_DIFF and motion[j] > CUT_RATIO * max(base, 0.01):
            out.append(j)
    return out


def best_window(analysis: dict, length: float, *, dark_ok: bool = False) -> dict | None:
    """Best start for a window of `length` seconds: {"start", "end", "score" 0–10, "cut_inside"}, or None."""
    if not analysis or not analysis.get("t"):
        return None
    times, duration = analysis["t"], float(analysis["duration"])
    length = min(float(length), duration)
    scores = _sample_scores(analysis, dark_ok=dark_ok)
    cut_at = set(cuts(analysis))
    best = None
    for i, start in enumerate(times):
        if start + length > duration + 0.05:
            break
        idx = [j for j in range(i, len(times)) if times[j] < start + length]
        if not idx:
            continue
        cut = any(j in cut_at for j in idx[1:])
        score = sum(scores[j] for j in idx) / len(idx) - (0.35 if cut else 0)
        if best is None or score > best["score"]:
            best = {"start": round(start, 2), "end": round(start + length, 2), "score": score, "cut_inside": cut}
    if best is None:
        return None
    best["score"] = round(max(0.0, best["score"]) * 10, 2)
    return best


def frame_jpeg(data: bytes, t: float, *, size: int = 384) -> bytes | None:
    """One JPEG frame at about `t` seconds (longest side `size` px), or None."""
    import av
    from PIL import Image

    try:
        with av.open(io.BytesIO(data)) as container:
            stream = container.streams.video[0]
            for frame in container.decode(stream):
                if float(frame.time or 0) + 1e-6 >= t:
                    image = frame.to_image()
                    image.thumbnail((size, size), Image.Resampling.LANCZOS)
                    out = io.BytesIO()
                    image.convert("RGB").save(out, "JPEG", quality=80)
                    return out.getvalue()
    except Exception as exc:  # noqa: BLE001
        log.info("Frame extraction failed: %s", exc)
    return None
