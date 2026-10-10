"""Render "Kalendern vs golfbagen" end to end: HyperFrames picture → music + synced SFX (sfx.json) → the cloud
editor's own finish step (−14 LUFS, H.264, Golfkuponger Spotlight outro, preview ≤ 9.5 MB).

    python render.py [--out work/gk-js-ad]
"""

import argparse
import json
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
NPX = shutil.which("npx") or shutil.which("npx.cmd") or "npx"


def mix(out: Path) -> Path:
    cfg = json.loads((HERE / "sfx.json").read_text(encoding="utf-8"))
    D = cfg["duration"]
    inputs = ["-i", str(HERE / cfg["music"])]
    chains = [f"[0:a]atrim=0:{D},asetpts=PTS-STARTPTS,volume={cfg['music_gain_db']}dB,aformat=sample_rates=48000:channel_layouts=stereo[m]"]
    labels = ["[m]"]
    for n, (t, name, db) in enumerate(cfg["events"], 1):
        inputs += ["-i", str(HERE / "assets" / "sfx" / name)]
        ms = int(t * 1000)
        chains.append(f"[{n}:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={db}dB,adelay={ms}|{ms},apad,atrim=0:{D}[s{n}]")
        labels.append(f"[s{n}]")
    chains.append("".join(labels) + f"amix=inputs={len(labels)}:duration=first:normalize=0,alimiter=limit=0.89[out]")
    target = out / "mix.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(chains), "-map", "[out]",
                    "-t", str(D), "-c:a", "pcm_s16le", str(target)], check=True)
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(REPO / "work" / "gk-js-ad"))
    out = Path(parser.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run([NPX, "--yes", "hyperframes@0.8.140", "render", str(HERE), "-o", str(out / "picture.mp4"),
                    "--fps", "30", "--crf", "12"], check=True)
    mix(out)
    finish = (REPO / "edit-renderer" / "src" / "finish.js").as_uri()
    outro = (REPO / "edit-renderer" / "outros" / "golfkuponger" / "spotlight-9x16.mp4").as_posix()
    o = out.as_posix() + "/"
    script = (f"import {{ finish }} from '{finish}';"
              f"const r = await finish({{ picture: '{o}picture.mp4', music: '{o}mix.wav', duration: 14, fps: 30, outDir: '{o}',"
              f" previewMax: Math.floor(9.5 * 1024 * 1024), masterMax: 80 * 1024 * 1024, outro: '{outro}' }});"
              "console.log(JSON.stringify(r, null, 1));")
    subprocess.run(["node", "--input-type=module", "-e", script], check=True)
