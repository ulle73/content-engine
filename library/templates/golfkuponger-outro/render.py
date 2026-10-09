"""Render the outro variants built by build.py and mux the original logo sound (unchanged, from t=0).

    python render.py [--out DIR] [--formats 9x16] [--variants klassisk,glod]

Writes <out>/<variant>-<fmt>.mp4 (H.264, yuv420p, faststart, AAC) plus a contact sheet <out>/sheet-<fmt>.png.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

import build

HYPERFRAMES = "hyperframes@0.8.140"
NPX = shutil.which("npx") or shutil.which("npx.cmd") or "npx"


def run(args: list[str]) -> None:
    subprocess.run(args, check=True)


def render(project: Path, out: Path) -> Path:
    picture = project / "picture.mp4"
    run([NPX, "--yes", HYPERFRAMES, "render", str(project), "-o", str(picture), "--fps", "30", "--crf", "14"])
    final = out / f"{project.name}.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-i", str(picture), "-i", str(project / "assets" / "logo-sound.wav"),
         "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", "-preset", "slow",
         "-c:a", "aac", "-b:a", "192k", "-af", "apad", "-t", str(build.DURATION), "-movflags", "+faststart", str(final)])
    return final


def sheet(videos: list[Path], out: Path, fmt: str) -> None:
    inputs, filters = [], []
    for i, v in enumerate(videos):
        inputs += ["-i", str(v)]
        filters.append(f"[{i}:v]select='eq(n\\,15)+eq(n\\,60)+eq(n\\,80)+eq(n\\,95)+eq(n\\,119)',scale=216:-1,tile=5x1[r{i}]")
    filters.append("".join(f"[r{i}]" for i in range(len(videos))) + f"vstack=inputs={len(videos)}[s]" if len(videos) > 1 else "[r0]copy[s]")
    run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(filters), "-map", "[s]", "-frames:v", "1",
         str(out / f"sheet-{fmt}.png")])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(build.HERE.parents[2] / "work" / "gk-outro"))
    parser.add_argument("--formats", default="9x16")
    parser.add_argument("--variants", default=",".join(build.VARIANTS))
    a = parser.parse_args()
    out = Path(a.out)
    projects = build.build(out / "projects", a.formats.split(","), a.variants.split(","))
    done = [render(p, out) for p in projects]
    for fmt in a.formats.split(","):
        sheet([v for v in done if v.stem.endswith(fmt)], out, fmt)
    for v in done:
        print(v)
