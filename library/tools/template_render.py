"""Shared render pipeline for the code-only HyperFrames templates in library/templates/<id>/.

Every template's render.py calls `main(...)`. The pipeline is the same one golfkuponger-js-ad uses:

    HyperFrames picture (index.html)  →  SFX + optional music mix (sfx.json)  →  edit-renderer/src/finish.js
    (−14 LUFS, H.264 master, optional brand outro appended, preview ≤ 9.5 MB)

plus review material for the critique loop (contact sheet one frame per second, mobile-size strip) and, with
--publish, the library preview (library/previews/<id>.mp4 ≤ 10 MB + <id>.jpg).

sfx.json:
    {
      "duration": 12,                       seconds of picture (outro excluded)
      "bpm": 120,                           beat grid the cuts sit on
      "music": "assets/music.mp3" | null,   optional bed; missing file = SFX only
      "music_gain_db": -4,
      "sounds": {"click": "library/kits/.../click.mp3", ...},   repo-relative paths (sounds already in the repo)
      "events": [[t_seconds, "click", gain_db], ...]
    }

Music can be generated locally for free with ACE-Step (CPU, ~4x realtime):
    cd C:\\Users\\rydqv\\video-tools\\ACE-Step-1.5
    uv run --no-sync python gen_track.py <seconds> <out.wav> "<caption>" <bpm>
then `ffmpeg -i out.wav -b:a 192k library/templates/<id>/assets/music.mp3`.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
NPX = shutil.which("npx") or shutil.which("npx.cmd") or "npx"
HYPERFRAMES = "hyperframes@0.8.140"
OUTROS = {"golfkuponger": REPO / "edit-renderer" / "outros" / "golfkuponger"}


def run(args: list[str], **kw) -> None:
    subprocess.run([str(a) for a in args], check=True, **kw)


def ffprobe_duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         check=True, capture_output=True, text=True).stdout.strip()
    return float(out or 0)


def picture(project: Path, out: Path, fps: int = 30) -> Path:
    target = out / "picture.mp4"
    run([NPX, "--yes", HYPERFRAMES, "render", project, "-o", target, "--fps", fps, "--crf", "12"])
    return target


def mix(here: Path, out: Path, *, has_clip_audio: bool = False) -> Path:
    """SFX events (+ music bed if present) → out/sfxmix.wav. Never named mix.wav: finish.js writes that file."""
    cfg = json.loads((here / "sfx.json").read_text(encoding="utf-8"))
    D = cfg["duration"]
    music = cfg.get("music")
    music_path = here / music if music else None
    inputs: list[str] = []
    chains: list[str] = []
    labels: list[str] = []
    if music_path and music_path.exists():
        inputs += ["-i", str(music_path)]
        fade = max(0.0, D - 0.6)
        chains.append(f"[0:a]atrim=0:{D},asetpts=PTS-STARTPTS,volume={cfg.get('music_gain_db', -4)}dB,"
                      f"aformat=sample_rates=48000:channel_layouts=stereo,afade=t=out:st={fade}:d=0.6,apad,atrim=0:{D}[m]")
        labels.append("[m]")
    else:
        inputs += ["-f", "lavfi", "-t", str(D), "-i", "anullsrc=r=48000:cl=stereo"]
        chains.append("[0:a]anull[m]")
        labels.append("[m]")
    sounds = cfg["sounds"]
    for n, (t, name, db) in enumerate(cfg["events"], 1):
        src = REPO / sounds[name]
        if not src.exists():
            raise FileNotFoundError(f"sfx '{name}' saknas: {src}")
        inputs += ["-i", str(src)]
        ms = int(round(t * 1000))
        chains.append(f"[{n}:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={db}dB,"
                      f"adelay={ms}|{ms},apad,atrim=0:{D}[s{n}]")
        labels.append(f"[s{n}]")
    chains.append("".join(labels) + f"amix=inputs={len(labels)}:duration=first:normalize=0,alimiter=limit=0.89[out]")
    target = out / "sfxmix.wav"
    run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(chains), "-map", "[out]",
         "-t", str(D), "-c:a", "pcm_s16le", target])
    return target


def finish(out: Path, *, duration: float, audio: Path, outro: Path | None, fps: int = 30) -> dict:
    finish_js = (REPO / "edit-renderer" / "src" / "finish.js").as_uri()
    o = out.as_posix() + "/"
    outro_arg = f"'{outro.as_posix()}'" if outro else "null"
    script = (f"import {{ finish }} from '{finish_js}';"
              f"const r = await finish({{ picture: '{o}picture.mp4', music: '{audio.as_posix()}', duration: {duration},"
              f" fps: {fps}, outDir: '{o}', previewMax: Math.floor(9.5 * 1024 * 1024), masterMax: 80 * 1024 * 1024,"
              f" outro: {outro_arg} }});"
              "console.log(JSON.stringify(r));")
    result = subprocess.run(["node", "--input-type=module", "-e", script], check=True, capture_output=True, text=True)
    data = json.loads(result.stdout.strip().splitlines()[-1])
    print(json.dumps(data, indent=1))
    return data


def review(video: Path, out: Path, *, duration: float, cols: int = 8, review_times: list[float] | None = None) -> None:
    """Contact sheet (one frame per second, incl. outro) + mobile-size strip (360 px wide frames)."""
    total = ffprobe_duration(video)
    n = max(1, int(total))
    rows = (n + cols - 1) // cols
    run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vf",
         f"fps=1,scale=200:-1,tile={cols}x{rows}:padding=4:color=0x222222", "-frames:v", "1", out / "sheet.png"])
    # mobile strip: six moments across the picture, at real phone width (360 px)
    times = [round(duration * k / 6 + 0.25, 2) for k in range(6)]
    if review_times:
        times = review_times
    select = "+".join(f"between(t\\,{t - 0.0165:.4f}\\,{t + 0.0165:.4f})" for t in times)
    run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vf", f"select='{select}',scale=360:-1,tile={len(times)}x1:padding=6",
         "-fps_mode", "vfr", "-frames:v", "1", out / "mobile.png"])


def publish(video: Path, item_id: str, *, still_at: float) -> None:
    """Library preview: 720p H.264 ≤ 10 MB in library/previews/<id>.mp4 + a still <id>.jpg."""
    previews = REPO / "library" / "previews"
    previews.mkdir(parents=True, exist_ok=True)
    mp4 = previews / f"{item_id}.mp4"
    for crf in (23, 26, 29, 32):
        run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vf", "scale=720:-2", "-c:v", "libx264", "-preset", "slow",
             "-crf", str(crf), "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", mp4])
        if mp4.stat().st_size <= 10 * 1000 * 1000:
            break
    run(["ffmpeg", "-v", "error", "-y", "-ss", str(still_at), "-i", video, "-frames:v", "1", "-vf", "scale=720:-2",
         "-q:v", "3", previews / f"{item_id}.jpg"])
    print(f"preview → {mp4} ({mp4.stat().st_size / 1e6:.1f} MB)")


def with_clip(here: Path, out: Path, clip: Path) -> Path:
    """Copy the template to out/project and swap the <!--CLIP-SLOT--> placeholder for a real <video>."""
    project = out / "project"
    if project.exists():
        shutil.rmtree(project)
    shutil.copytree(here, project, ignore=shutil.ignore_patterns("render.py", "__pycache__", "*.md"))
    shutil.copy(clip, project / "assets" / "clip.mp4")
    html = (project / "index.html").read_text(encoding="utf-8")
    cfg = json.loads((here / "sfx.json").read_text(encoding="utf-8"))
    video = (f'<video id="ugc-clip" class="clip" src="assets/clip.mp4" playsinline data-has-audio="true" '
             f'data-start="0" data-duration="{cfg["duration"]}" data-track-index="0"></video>')
    html, count = re.subn(r"<!--CLIP-SLOT-->.*?<!--/CLIP-SLOT-->", video, html, flags=re.S)
    if not count:
        raise SystemExit("index.html saknar <!--CLIP-SLOT--> … <!--/CLIP-SLOT-->")
    (project / "index.html").write_text(html, encoding="utf-8")
    return project


def main(here: Path, *, item_id: str, work_name: str, outro: str | None = None, still_at: float = 3.0,
         clip_slot: bool = False, review_times: list[float] | None = None) -> None:
    parser = argparse.ArgumentParser(description=f"Render {item_id}")
    parser.add_argument("--out", default=str(REPO / "work" / work_name))
    parser.add_argument("--format", default="9x16", help="outro format (9x16, 4x5, 1x1)")
    parser.add_argument("--publish", action="store_true", help="write library/previews/<id>.mp4 + .jpg")
    parser.add_argument("--skip-picture", action="store_true", help="reuse out/picture.mp4 (audio-only changes)")
    if clip_slot:
        parser.add_argument("--clip", help="real UGC clip (9:16 mp4) that replaces the placeholder")
    a = parser.parse_args()
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    cfg = json.loads((here / "sfx.json").read_text(encoding="utf-8"))
    project = here
    if clip_slot and a.clip:
        project = with_clip(here, out, Path(a.clip).resolve())
    if not a.skip_picture:
        picture(project, out)
    audio = mix(here, out)
    outro_file = (OUTROS[outro] / f"spotlight-{a.format}.mp4") if outro else None
    result = finish(out, duration=cfg["duration"], audio=audio, outro=outro_file)
    final = Path(result["master"])
    review(final, out, duration=cfg["duration"], review_times=review_times)
    print(f"klar: {final}\n  kontaktkarta: {out / 'sheet.png'}\n  mobilvy: {out / 'mobile.png'}")
    if a.publish:
        publish(final, item_id, still_at=still_at)
