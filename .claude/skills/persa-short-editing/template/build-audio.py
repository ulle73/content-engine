#!/usr/bin/env python3
"""
tp-0923 audio — three parts.

    python3 build-audio.py            # -> out/tp-0925b-audio.wav (+ out/sfx-only.wav)

  1 VOICE  assets/recording.mp4, untouched and un-levelled (mean -19.1 / peak -1.7).
  2 BED    broll-library/bgm/house-bed-loop.m4a at 1.0 — it is pre-levelled to -34 LUFS, a
           LOUDNESS target, never a peak target (bed-peak-vs-lufs). It runs from 0: he talks
           from the first frame, so there is no silent open to leave bare.
  3 SFX    sfx-cues.txt, mixed by the same maths mix-sfx.sh uses, written out ON ITS OWN as
           out/sfx-only.wav so every cue can be measured against SILENCE. AAC subtraction does
           not cancel and a voice-nulled mix lies about the level (sfx-null-on-silence).
"""
import pathlib, subprocess, sys

def _find_skill(start):
    """The skill lives in <repo>/.claude/skills/persa-short-editing; videos live in
    <repo>/work/persa-short/videos/<slug>/ (content-engine layout), so walk up to find it."""
    for p in [start.resolve(), *start.resolve().parents]:
        s = p / ".claude" / "skills" / "persa-short-editing"
        if s.exists():
            return s
    sys.exit(f"cannot find .claude/skills/persa-short-editing above {start}")

D = pathlib.Path(__file__).parent
SKILL = _find_skill(D)
REPO = SKILL.parents[2]
DUR = 95.80

cues = []
for ln in (D / "sfx-cues.txt").read_text(encoding="utf-8").splitlines():
    ln = ln.strip()
    if not ln or ln.startswith("#"):
        continue
    t, name, *rest = ln.split()
    cues.append((float(t), name, float(rest[0]) if rest else 0.12))


def sfx_path(name):
    for ext in ("", ".wav", ".mp3", ".aif", ".aiff"):
        p = SKILL / "sfx" / (name + ext)
        if p.exists():
            return p
    sys.exit(f"no sound: {name}")


def mix_sfx(out):
    ins, filt, labels = [], [], ""
    filt.append(f"anullsrc=r=48000:cl=stereo,atrim=0:{DUR:.3f}[base]")
    labels += "[base]"
    for k, (t, name, g) in enumerate(cues):
        ins += ["-i", str(sfx_path(name))]
        filt.append(f"[{k}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
                    f"volume={g},adelay={int(t*1000)}|{int(t*1000)}[s{k}]")
        labels += f"[s{k}]"
    filt.append(f"{labels}amix=inputs={len(cues)+1}:normalize=0:duration=first[m]")
    filt.append(f"[m]atrim=0:{DUR:.3f},asetpts=N/SR/TB[a]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", ";".join(filt),
                    "-map", "[a]", "-c:a", "pcm_s24le", "-ar", "48000", str(out)], check=True)


bed = None
for cand in (REPO / "broll-library/bgm/house-bed-loop.m4a", SKILL / "bgm/house-bed-loop.m4a"):
    if cand.exists():
        bed = cand
        break
assert bed, "no bed"

(D / "out").mkdir(exist_ok=True)
mix_sfx(D / "out/sfx-only.wav")
print("wrote out/sfx-only.wav —", len(cues), "cues on SILENCE (the only valid control)")

g = [
    f"[0:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
    f"atrim=0:{DUR:.3f},asetpts=N/SR/TB[vo]",
    f"[1:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,volume=1.0,"
    f"atrim=0:{DUR:.3f},asetpts=N/SR/TB[bed]",
    f"[2:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[sfx]",
    "[vo][bed][sfx]amix=inputs=3:normalize=0:duration=first[mx]",
    f"[mx]atrim=0:{DUR:.3f},asetpts=N/SR/TB,alimiter=limit=0.94:level=disabled[a]",
]
subprocess.run(["ffmpeg", "-v", "error", "-y",
                "-i", str(D / "assets/recording.mp4"),
                "-stream_loop", "-1", "-i", str(bed),
                "-i", str(D / "out/sfx-only.wav"),
                "-filter_complex", ";".join(g), "-map", "[a]",
                "-c:a", "pcm_s24le", "-ar", "48000", str(D / "out/tp-0925b-audio.wav")], check=True)
print("wrote out/tp-0925b-audio.wav")
