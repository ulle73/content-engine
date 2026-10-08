#!/usr/bin/env python3
"""
Decode a camera original to a Rec.709 SDR mezzanine BEFORE anything else touches it.

Every downstream tool — rvm-matte.py, make-grade-filter.py --derive, find-cut-line.py, the
contrast gate, HyperFrames itself — assumes Rec.709 display footage. Feed any of them a LOG or
HLG file and they measure the encoding, not the picture: RVM segments a flat grey image worse,
--derive "corrects" the log curve as if it were the room's lighting, and the render ships washed
out. So this runs first, once, and its output becomes assets/recording.mp4.

    python scripts/camera-decode.py --src DJI_20260913_0001_D.MP4 --out assets/recording.mp4
    python scripts/camera-decode.py --src clip.MP4 --out rec.mp4 --mode dlogm --lut ~/luts/x.cube
    python scripts/camera-decode.py --src clip.MOV --probe          # report, write nothing

MODES (auto-detected unless --mode is given):
  hlg    color_transfer=arib-std-b67. The DJI "HLG" colour profile, and what DJI Mimo exports
         carry. Tone-mapped to Rec.709 by maths — no LUT needed.
  dlogm  DJI D-Log M. The container does NOT say so (it is tagged like ordinary 709 or not at
         all), so auto-detection is a FLATNESS test on the picture, and it is only a hint:
         pass --mode dlogm to be sure. Needs DJI's own D-Log M -> Rec.709 LUT (--lut).
  709    already display-referred. Passed through (scaled/fps only).

THE LUT IS NOT IN THE PACKAGE. It is DJI's file, free from the Osmo Pocket 3 downloads page
(dji.com -> Osmo Pocket 3 -> Downloads -> "D-Log M to Rec.709 LUT"). Put it at
work/persa-short/luts/dji-dlogm-rec709.cube (repo root) and this script finds it without --lut.

Why the pipeline is shaped the way it is:
  * The LUT runs in 32-bit float RGB (gbrpf32le), with tetrahedral interpolation. D-Log M is
    10-bit; applying a LUT after dropping to 8-bit posterises skies and skin into bands.
  * 8-bit happens ONCE, at the very end, after the curve has already spread the tones.
  * This is a TECHNICAL decode, not a look. It is not a grade and it is not "darkening the
    picture" (see never-darken-the-picture): a log file is not a picture yet. The creative
    grade, if the style has one, is derived from THIS output, never from the log file.
"""
import argparse, json, os, pathlib, subprocess, sys

# content-engine: the LUT lives in <repo>/work/persa-short/luts/ (or PERSA_LUT=<path>), never in ~/.cache
DEFAULT_LUT = pathlib.Path(os.environ.get("PERSA_LUT") or
                           pathlib.Path(__file__).resolve().parents[4] / "work/persa-short/luts/dji-dlogm-rec709.cube")


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw).stdout


def probe(src):
    j = json.loads(run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_streams",
                        "-show_format", "-of", "json", src]))
    return j["streams"][0], j["format"]


def flatness(src, dur):
    """Luma p1/p99 and mean chroma over 5 frames. Log footage has no blacks, no whites and
    almost no saturation; a normal 709 take has all three."""
    import numpy as np
    ps, chroma = [], []
    for k in range(5):
        t = dur * (k + 0.5) / 5
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", src, "-frames:v", "1",
                              "-vf", "scale=270:-2", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                             capture_output=True).stdout
        a = np.frombuffer(raw, np.uint8).astype(float).reshape(-1, 3)
        if not len(a):
            continue
        y = a @ [0.299, 0.587, 0.114]
        ps.append(np.percentile(y, [1, 99]))
        chroma.append((a.max(1) - a.min(1)).mean())
    p = np.mean(ps, 0)
    return float(p[0]), float(p[1]), float(np.mean(chroma))


def main():
    ap = argparse.ArgumentParser(description="camera original -> Rec.709 mezzanine")
    ap.add_argument("--src", required=True)
    ap.add_argument("--out")
    ap.add_argument("--mode", choices=["auto", "hlg", "dlogm", "709"], default="auto")
    ap.add_argument("--lut", help=f"D-Log M -> Rec.709 .cube (default {DEFAULT_LUT})")
    ap.add_argument("--fps", type=float, help="resample to this fps (default: keep source)")
    ap.add_argument("--size", default="1080x1920", help="WxH, or 'keep'")
    ap.add_argument("--crf", type=int, default=14)
    ap.add_argument("--probe", action="store_true", help="report the detection and stop")
    a = ap.parse_args()

    st, fm = probe(a.src)
    dur = float(fm.get("duration", st.get("duration", 10)))
    trc, pix = st.get("color_transfer", "unknown"), st.get("pix_fmt", "")
    p1, p99, chroma = flatness(a.src, dur)
    tenbit = "10" in pix or "12" in pix

    mode = a.mode
    if mode == "auto":
        if trc == "arib-std-b67":
            mode = "hlg"
        elif trc in ("smpte2084",):
            sys.exit("camera-decode: PQ/HDR10 source — not a DJI profile this script handles")
        elif p1 > 28 and p99 < 225 and chroma < 22:
            mode = "dlogm"
        else:
            mode = "709"

    print(f"camera-decode: {st['width']}x{st['height']} {pix} trc={trc} "
          f"| luma p1 {p1:.0f} p99 {p99:.0f} chroma {chroma:.1f} -> mode {mode}")
    if mode == "dlogm" and a.mode == "auto":
        print("  ⚠ D-Log M is detected from FLATNESS, not metadata. Confirm with --mode dlogm.")
    if mode in ("hlg", "dlogm") and not tenbit:
        print("  ⚠ 8-bit log/HLG: the camera was not in 10-bit, expect banding after the decode.")
    if mode == "709" and p1 > 20 and chroma < 26:
        print("  ⚠ looks flat for 709. If this is D-Log M, rerun with --mode dlogm.")
    if a.probe:
        return
    if not a.out:
        sys.exit("camera-decode: --out is required unless --probe")

    chain = []
    if mode == "hlg":
        # npl=203 puts HLG reference white where SDR expects it. Operator chosen 2026-09-13 on
        # a real Pocket 3 HLG take against DJI Mimo's own SDR export of the same session
        # (chroma 26.8): reinhard 0.6 / desat 2 -> chroma 26.5, white wall neutral 232/234/225.
        # mobius desat=0 tinted the wall green-yellow (216/224/196) and pushed skin orange
        # (chroma 37); hable blew the highlights and greyed the frame (chroma 15.6).
        chain += ["zscale=tin=arib-std-b67:min=bt2020nc:pin=bt2020:rin=tv:t=linear:npl=203",
                  "format=gbrpf32le", "zscale=p=bt709",
                  "tonemap=tonemap=reinhard:param=0.6:desat=2",
                  "zscale=t=bt709:m=bt709:r=tv"]
    elif mode == "dlogm":
        lut = pathlib.Path(a.lut).expanduser() if a.lut else DEFAULT_LUT
        if not lut.exists():
            sys.exit(f"camera-decode: D-Log M needs DJI's Rec.709 LUT and it is not at {lut}.\n"
                     "  Download it free from dji.com (Osmo Pocket 3 -> Downloads) and pass --lut,\n"
                     f"  or save it as {DEFAULT_LUT}.")
        esc = str(lut).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
        chain += ["format=gbrpf32le", f"lut3d=file='{esc}':interp=tetrahedral"]

    if a.fps:
        chain.append(f"fps={a.fps}")
    if a.size != "keep":
        w, h = a.size.split("x")
        # cover-fit then centre-crop, so a 16:9 source becomes a 9:16 slice and never letterboxes
        chain += [f"scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos",
                  f"crop={w}:{h}"]
    chain.append("format=yuv420p")

    cmd = ["ffmpeg", "-v", "error", "-y", "-i", a.src, "-vf", ",".join(chain),
           "-c:v", "libx264", "-preset", "slow", "-crf", str(a.crf),
           "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
           "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", a.out]
    subprocess.run(cmd, check=True)
    q1, q99, qc = flatness(a.out, dur)
    print(f"  wrote {a.out} | luma p1 {q1:.0f} p99 {q99:.0f} chroma {qc:.1f}")


if __name__ == "__main__":
    main()
