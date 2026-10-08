#!/usr/bin/env python3
"""
Tighten a long-form recording: remove dead air between words and REMAP the transcript
onto the new timeline.

This is the FIRST step of a NextPhase long-form edit. A 15-minute improvised recording
carries minutes of half-second pauses that a 45-second short never accumulates. Cutting
them is the cheapest retention win available — but it moves every single word onset, so
the transcript must be remapped in the same operation or every graphic in the edit ends
up early.

    python scripts/tighten-cuts.py \
        --src assets/recording.mp4 \
        --transcript assets/transcript.json \
        --max-gap 0.55 --pad 0.12 \
        --out assets/recording-tight.mp4

Writes
    assets/recording-tight.mp4     the tightened video
    assets/transcript-tight.json   the transcript with every start/end remapped
    assets/cuts.json               the kept spans + what was removed (auditable)

AFTER THIS RUNS, transcript-tight.json IS THE ONLY TIMING SOURCE. Timing a graphic
against the original transcript is the #1 way this edit goes wrong, and it looks like
"the graphics are all slightly early" rather than like a bug.

Note on the look: these are hard jump cuts, which is the intended house style — the
layout rotation and b-roll cover most of them. Use --min-remove to avoid a swarm of
tiny visible cuts that buy no time.
"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _win_utf8  # noqa: E402,F401  content-engine import: UTF-8 text I/O on Windows
import argparse, json, os, shutil, subprocess, sys, tempfile

FILLERS = {"um", "uh", "erm", "hmm", "mmm", "uhh", "umm", "ah", "eh"}


# ── transcript I/O ────────────────────────────────────────────────────────────
def load_words(path):
    """Return (words, container) where words is a list of dicts with start/end.

    Handles the shapes hyperframes/parakeet and friends actually emit:
      [ {text,start,end}, ... ]                     <- the house format
      { "words":    [ {word|text,start,end}, ... ] }
      { "segments": [ { "words": [...] }, ... ] }
    The word dicts are returned BY REFERENCE so remapping mutates the original
    container and we can dump it back with every other field intact.
    """
    with open(path) as f:
        doc = json.load(f)

    if isinstance(doc, list):
        words = doc
    elif isinstance(doc, dict) and isinstance(doc.get("words"), list):
        words = doc["words"]
    elif isinstance(doc, dict) and isinstance(doc.get("segments"), list):
        words = [w for s in doc["segments"] for w in s.get("words", [])]
        if not words:
            sys.exit("tighten: 'segments' present but no per-word timings — "
                     "re-transcribe with word-level output.")
    else:
        sys.exit(f"tighten: unrecognised transcript shape in {path}")

    bad = [w for w in words if "start" not in w or "end" not in w]
    if bad:
        sys.exit(f"tighten: {len(bad)} entries lack start/end — need a word-level transcript.")
    return words, doc


def text_of(w):
    return str(w.get("text", w.get("word", ""))).strip()


# ── planning ──────────────────────────────────────────────────────────────────
def probe_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", path],
        capture_output=True, text=True, check=True).stdout.strip()
    return float(out)


def plan_keeps(words, duration, max_gap, pad, min_remove, drop_fillers):
    """Build the list of [start, end] spans to KEEP, plus the words that survive."""
    kept_words = []
    for i, w in enumerate(words):
        if drop_fillers and text_of(w).lower().strip(".,!?") in FILLERS:
            # Only drop an ISOLATED filler — one with real silence on both sides.
            # Excising a filler wedged between words leaves an audible glitch.
            before = w["start"] - words[i - 1]["end"] if i else 99.0
            after = words[i + 1]["start"] - w["end"] if i + 1 < len(words) else 99.0
            if before >= 0.15 and after >= 0.15:
                continue
        kept_words.append(w)

    if not kept_words:
        sys.exit("tighten: no words survived — check the transcript.")

    keeps = []
    span_start = max(0.0, kept_words[0]["start"] - pad)
    for i in range(len(kept_words) - 1):
        gap = kept_words[i + 1]["start"] - kept_words[i]["end"]
        if gap <= max_gap:
            continue
        cut_from = kept_words[i]["end"] + pad
        cut_to = max(cut_from, kept_words[i + 1]["start"] - pad)
        if cut_to - cut_from < min_remove:      # not worth a visible cut
            continue
        keeps.append([span_start, cut_from])
        span_start = cut_to
    keeps.append([span_start, min(duration, kept_words[-1]["end"] + pad)])

    keeps = [k for k in keeps if k[1] - k[0] > 0.02]
    return keeps, kept_words


def remap(words, keeps):
    """Shift each word onto the tightened timeline. Words inside a removed span are
    dropped (only reachable via --drop-fillers)."""
    # offsets[i] = total time removed before keeps[i] starts
    offsets, removed = [], 0.0
    prev_end = 0.0
    for a, b in keeps:
        removed += a - prev_end
        offsets.append(removed)
        prev_end = b

    out = []
    for w in words:
        for (a, b), off in zip(keeps, offsets):
            if a - 1e-6 <= w["start"] < b + 1e-6:
                w = dict(w)
                w["start"] = round(w["start"] - off, 3)
                w["end"] = round(min(w["end"], b) - off, 3)
                out.append(w)
                break
    return out


# ── encode ────────────────────────────────────────────────────────────────────
def encode(src, keeps, out, fps, crf, has_audio):
    parts, labels = [], ""
    for i, (a, b) in enumerate(keeps):
        parts.append(f"[0:v]trim=start={a:.4f}:end={b:.4f},setpts=PTS-STARTPTS[v{i}];")
        labels += f"[v{i}]"
        if has_audio:
            parts.append(f"[0:a]atrim=start={a:.4f}:end={b:.4f},asetpts=PTS-STARTPTS[a{i}];")
            labels += f"[a{i}]"
    n = len(keeps)
    if has_audio:
        parts.append(f"{labels}concat=n={n}:v=1:a=1[vout][aout]")
    else:
        parts.append(f"{labels}concat=n={n}:v=1:a=0[vout]")

    # The graph is far too long for argv on a 15-minute file — hand it to ffmpeg as a script.
    fd, script = tempfile.mkstemp(suffix=".txt", text=True)
    with os.fdopen(fd, "w") as f:
        f.write("".join(parts))

    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-stats", "-i", src,
           "-/filter_complex", script,   # ffmpeg 7.1+: -filter_complex_script was removed (import fix)
            "-map", "[vout]"]
    if has_audio:
        cmd += ["-map", "[aout]", "-c:a", "aac", "-b:a", "256k"]
    cmd += ["-c:v", "libx264", "-crf", str(crf), "-preset", "medium",
            "-pix_fmt", "yuv420p", "-r", str(fps), out]
    try:
        subprocess.run(cmd, check=True)
    finally:
        os.unlink(script)


def main():
    p = argparse.ArgumentParser(description="Tighten dead air and remap the transcript")
    p.add_argument("--src", required=True)
    p.add_argument("--transcript", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--max-gap", type=float, default=0.55,
                   help="silence longer than this gets cut (default 0.55s)")
    p.add_argument("--pad", type=float, default=0.12,
                   help="breath left on each side of a cut (default 0.12s). Below ~0.08 "
                        "words clip and it sounds rushed.")
    p.add_argument("--min-remove", type=float, default=0.10,
                   help="skip a cut that would save less than this (default 0.10s) — "
                        "avoids a swarm of visible cuts that buy no time")
    p.add_argument("--drop-fillers", action="store_true",
                   help="also drop ISOLATED um/uh (silence >=0.15s on both sides). "
                        "Off by default: mid-phrase excision glitches.")
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--crf", type=int, default=18)
    p.add_argument("--dry-run", action="store_true", help="report + write cuts.json, no encode")
    a = p.parse_args()

    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            sys.exit(f"tighten: {tool} not on PATH. "
                     f'(Windows: node/npx ligger redan på PATH)')

    words, _ = load_words(a.transcript)
    duration = probe_duration(a.src)

    span = words[-1]["end"] - words[0]["start"]
    if duration - span > 0.7:
        print(f"  ! transcript covers {span:.1f}s of a {duration:.1f}s file "
              f"({duration - span:.1f}s unaccounted). Gap-check before trusting this "
              f"— Parakeet drops audio silently.")

    has_audio = bool(subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0",
         "-show_entries", "stream=codec_type", "-of", "csv=p=0", a.src],
        capture_output=True, text=True).stdout.strip())
    if not has_audio:
        print("  ! source has no audio track")

    keeps, kept_words = plan_keeps(words, duration, a.max_gap, a.pad,
                                   a.min_remove, a.drop_fillers)
    new_dur = sum(b - x for x, b in keeps)

    print(f"tighten: {a.src}")
    print(f"  words        {len(words)} -> {len(kept_words)}")
    print(f"  duration     {duration:7.2f}s -> {new_dur:7.2f}s "
          f"(saved {duration - new_dur:.2f}s, {100 * (duration - new_dur) / duration:.1f}%)")
    print(f"  cuts         {len(keeps) - 1}")

    base = os.path.dirname(a.out) or "."
    cuts_path = os.path.join(base, "cuts.json")
    with open(cuts_path, "w") as f:
        json.dump({"source": a.src, "source_duration": round(duration, 3),
                   "tight_duration": round(new_dur, 3),
                   "max_gap": a.max_gap, "pad": a.pad,
                   "drop_fillers": a.drop_fillers,
                   "keeps": [[round(x, 3), round(b, 3)] for x, b in keeps]}, f, indent=2)
    print(f"  wrote        {cuts_path}")

    tight = remap(words, keeps)
    tpath = os.path.join(os.path.dirname(a.transcript) or ".", "transcript-tight.json")
    with open(tpath, "w") as f:
        json.dump(tight, f, indent=1)
    print(f"  wrote        {tpath}   <- THE ONLY TIMING SOURCE FROM NOW ON")

    if a.dry_run:
        print("  (dry run — no encode)")
        return

    encode(a.src, keeps, a.out, a.fps, a.crf, has_audio)
    print(f"  wrote        {a.out}")
    print(f"\n  Sanity-check before building: pick 3 words from {os.path.basename(tpath)} "
          f"(one early, one middle, one late) and confirm each lands on its word in the "
          f"tightened file:\n    ffmpeg -ss <t> -i {a.out} -frames:v 1 work/nextphase/tmp/check.jpg")


if __name__ == "__main__":
    main()
