#!/usr/bin/env python3
"""
Deliver tp-0923 WITHOUT the camera ever passing through the browser
(browser-render-tints-camera): Chrome's decode shifts G by about +4 on identical tags, so his
picture is never handed to it. Every designed surface renders as a transparent layer and is
composited onto the untouched recording here, in ffmpeg.

    python3 composite.py out/tp-0923-visual.mp4                  # voice straight off the take
    python3 composite.py out/x.mp4 --audio out/tp-0923c-audio.wav # the full mix

Per beat: recording.mp4 placed (face 1:1 · card at THIS ACT's solve · CTA bottom half), then
out/mid.mov (the picture, carrying the rounded card HOLE, and the display type that sits BEHIND
him), then his cutout = the SAME YUV alphamerged with the RVM alpha (no RGB round trip, so it
sits invisibly on the camera), then out/fg.mov over the whole timeline.

The layer order IS the persa technique: raw camera -> the type -> the matte at 1:1 -> captions.
Type he occludes reads painted on the wall behind him; type floating clear of him reads pasted.

⚠ ONE camera solve: this take holds ONE framing for all 67s (the 10 fps cut scan peaks at
10.6, against 20+ on the two takes that really cut). The solve still runs through the same
per-act table, so a take that does cut needs nothing changed here.
"""
import argparse, json, pathlib, subprocess

D = pathlib.Path(__file__).parent
ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("--audio", default=None)
a = ap.parse_args()

GEO = json.loads((D / "assets/geometry.json").read_text(encoding="utf-8"))
CAMS, ACTS = GEO["cam"], GEO["acts"]
BEATS = json.load(open(D / "beats.json", encoding="utf-8"))
FPS = 30
NF = 2874
FACE_TYPE = set(json.load(open(D / "assets/face_type.json", encoding="utf-8")))


def act_of(t):
    for s, e, k in ACTS:
        if s <= t < e:
            return k
    return ACTS[-1][2]


tmp = D / "work"
tmp.mkdir(exist_ok=True)
parts = []
for i, (s, e, kind) in enumerate(BEATS):
    f0, f1 = round(s * FPS), min(NF, round(e * FPS))
    dur = (f1 - f0) / FPS
    CAM = CAMS[act_of(s)]
    tr = f"trim=start_frame={f0}:end_frame={f1},setpts=PTS-STARTPTS"
    g = [f"[0:v]{tr},format=yuv420p,split[c][k]", f"[1:v]{tr},format=gray[al]", f"[2:v]{tr}[mm]",
         "[k][al]alphamerge,format=yuva444p[pp]", "[c]format=yuv444p[cc]"]
    if kind == "face":
        base, person = "[cc]", "[pp]"
    elif kind == "ui":
        g += [f"color=c=black:s=1080x1920:r=30:d={dur:.4f},format=yuv444p[bk]",
              f"[cc]scale={CAM['width']}:{CAM['height']}:flags=lanczos[cs]",
              f"[bk][cs]overlay=x={CAM['left']}:y={CAM['top']}:format=yuv444[cb]",
              f"color=c=black@0:s=1080x1920:r=30:d={dur:.4f},format=yuva444p[pb]",
              f"[pp]scale={CAM['width']}:{CAM['height']}:flags=lanczos[ps]",
              f"[pb][ps]overlay=x={CAM['left']}:y={CAM['top']}:format=yuv444[pc]"]
        base, person = "[cb]", "[pc]"
    elif kind == "broll":   # B-ROLL FULL — no camera: black under the mid layer, which paints all of it
        g += [f"color=c=black:s=1080x1920:r=30:d={dur:.4f},format=yuv444p[bk]", "[cc]nullsink", "[pp]nullsink"]
        base, person = "[bk]", None
    else:   # cta — cream top half, HIM in the bottom half (cta-is-half-and-half)
        g += [f"[cc]crop=1080:960:0:{GEO['full_top']},pad=1080:1920:0:960:color=black[cb]",
              "[pp]nullsink"]
        base, person = "[cb]", None
    if person and (kind == "ui" or i in FACE_TYPE):
        g += [f"{base}[mm]overlay=format=yuv444[bm]", f"[bm]{person}overlay=format=yuv444,format=yuv444p[v]"]
    else:
        if person:
            g.append(f"{person}nullsink")
        g.append(f"{base}[mm]overlay=format=yuv444,format=yuv444p[v]")
    part = tmp / f"seg{i:02d}.mkv"
    subprocess.run(["ffmpeg", "-v", "error", "-y",
                    "-i", str(D / "assets/recording.mp4"), "-i", str(D / "assets/alpha.mkv"),
                    "-i", str(D / "out/mid.mov"), "-filter_complex", ";".join(g), "-map", "[v]",
                    "-frames:v", str(f1 - f0), "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "10", "-pix_fmt", "yuv444p", str(part)], check=True)
    parts.append(part)
    print("seg", i, kind, act_of(s), f1 - f0, "frames")

(tmp / "concat.txt").write_text("".join(f"file '{pathlib.Path(x).as_posix()}'\n" for x in parts), encoding="utf-8")
ins = ["-f", "concat", "-safe", "0", "-i", str(tmp / "concat.txt"), "-i", str(D / "out/fg.mov"),
       "-i", a.audio or str(D / "assets/recording.mp4")]
g = ["[0:v][1:v]overlay=format=yuv444,format=yuv420p,"
     "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv[v]"]
cmd = ["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", ";".join(g), "-map", "[v]",
       "-map", "2:a",
       "-c:v", "libx264", "-preset", "slow", "-crf", "15", "-profile:v", "high", "-level", "4.2",
       "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv",
       "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart",
       str(D / a.out)]
subprocess.run(cmd, check=True)
print("wrote", a.out)
