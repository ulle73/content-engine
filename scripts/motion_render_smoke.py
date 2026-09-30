"""Real renderer evaluation. Synthetic fixture only; no private user uploads in CI."""

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
import numpy as np
import psutil

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine.motion.planner import compile_template
from engine.motion.brand import PRESETS

DEST = Path(os.environ.get("MOTION_EVIDENCE_DIR", str(ROOT / "motion-evidence")))
DEST.mkdir(parents=True, exist_ok=True)
brand = {**PRESETS["golfkuponger"], "name": "Golfkuponger", "logo_asset_id": None}
results = []

for mode, ratio in [("preview", "9:16"), ("final", "9:16"), ("final", "1:1"), ("final", "16:9")]:
    folder = DEST / (mode + "-" + ratio.replace(":", "x"))
    folder.mkdir(exist_ok=True)
    spec = compile_template(
        "monthly-wrapped",
        {"month": "September", "count": 877, "total": 721515, "area": "Stockholm"},
        aspect_ratio=ratio,
    )
    job = {"spec": spec, "brand": brand, "files": {}, "outputDir": str(folder), "mode": mode}
    (folder / "job.json").write_text(json.dumps(job))
    maximum = [0]
    started = time.monotonic()
    with (folder / "render.log").open("w") as log:
        process = subprocess.Popen(
            ["node", "render.mjs", str(folder / "job.json")],
            cwd=ROOT / "motion-renderer",
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        while process.poll() is None:
            try:
                parent = psutil.Process(process.pid)
                rss = sum(p.memory_info().rss for p in [parent, *parent.children(recursive=True)] if p.is_running())
                maximum[0] = max(maximum[0], rss)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            time.sleep(0.25)
        if process.returncode:
            print((folder / "render.log").read_text())
            raise SystemExit(process.returncode)
    video = folder / (mode + ".mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-f", "null", "-"], check=True)
    info = json.loads(
        subprocess.check_output(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)])
    )
    pcm = subprocess.check_output(
        ["ffmpeg", "-v", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", "22050", "-f", "f32le", "-"]
    )
    samples = np.frombuffer(pcm, dtype="<f4")
    peak = float(np.max(np.abs(samples)))
    rms = float(np.sqrt(np.mean(samples * samples)))
    assert peak > 0.001 and peak < 1, "Audio is silent or clipping"
    result = {
        "mode": mode,
        "ratio": ratio,
        "seconds_elapsed": round(time.monotonic() - started, 2),
        "peak_rss_mb": round(maximum[0] / 1024**2, 1),
        "audio_peak": peak,
        "audio_rms": rms,
        "probe": info,
    }
    results.append(result)
    (DEST / "smoke-results.json").write_text(json.dumps(results, indent=2))
    print(mode, ratio, "rendered and fully decoded, peak RSS", result["peak_rss_mb"], "MB", flush=True)
