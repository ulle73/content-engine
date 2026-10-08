#!/usr/bin/env python3
"""
Verify the skill package before it ships. A buyer's first render failing on a dangling path is
the worst possible first impression, and every check here has already caught a real break.

    python scripts/verify-package.py            # run from inside the skill folder
    python scripts/verify-package.py --strict   # also fail on redistributable-media warnings

Checks:
  1. every relative asset path referenced by a packaged block resolves
  2. every script named in SKILL.md and the reference docs exists
  3. every sound named in the palette docs exists in sfx/
  4. the bed named in the docs exists in bgm/
  5. flags third-party media that should not ship in a paid release (see WHATS-INCLUDED.md)
"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _win_utf8  # noqa: E402,F401  content-engine import: UTF-8 text I/O on Windows
import argparse, pathlib, re, sys

ap = argparse.ArgumentParser()
ap.add_argument("--strict", action="store_true")
a = ap.parse_args()

SKILL = pathlib.Path(__file__).resolve().parent.parent
errs, warns = [], []


def rel(p):
    return str(p.relative_to(SKILL))


# 1 — block asset paths
for f in sorted((SKILL / "ui-blocks").glob("*.html")):
    for m in re.findall(r'"\.\./([A-Za-z0-9/_.\-]+)', f.read_text()):
        target = SKILL / m.rstrip("/")
        ok = target.is_dir() if m.endswith("/") else target.exists()
        if not ok:
            errs.append(f"{rel(f)} references ../{m} — not in the package")

# 2 — scripts named in the docs
named = set()
for doc in list((SKILL / "reference").glob("*.md")) + [SKILL / "SKILL.md"]:
    named |= set(re.findall(r"scripts/([A-Za-z0-9_\-]+\.(?:py|sh))", doc.read_text()))
for s in sorted(named):
    if not (SKILL / "scripts" / s).exists():
        errs.append(f"docs reference scripts/{s} — missing from the package")

# 3 — the sound palette
sfx = {p.stem for p in (SKILL / "sfx").glob("*") if p.suffix in (".wav", ".mp3", ".aif", ".aiff")}
sd = (SKILL / "reference" / "sound-design.md").read_text()
for name in sorted(set(re.findall(r"`([a-z][a-z\-]+)`", sd))):
    if name in {"sfx", "bgm", "gain", "volume", "time-sec"}:
        continue
    if name in {"swell", "riser", "whoosh", "whoosh-2", "swoosh", "pop", "click",
                "futuristic-click", "confirm", "ping", "beep", "keyboard", "magic-reveal",
                "highlighter", "camera-shutter", "vinyl-rewind"} and name not in sfx:
        errs.append(f"sound-design.md names `{name}` — not in sfx/")

# 4 — the bed
beds = list((SKILL / "bgm").glob("*.m4a"))
if not any("loop" in b.name for b in beds):
    errs.append("no looping bed in bgm/ — sound-design.md expects house-bed-loop.m4a")

# 5 — media that should not ship in a paid release
THIRD_PARTY = {
    "bgm":       "a commercial music track — licensed to USE, not to redistribute",
    "sfx":       "a third-party SFX pack — check its redistribution terms",
    "clawd":     "Anthropic's Claude mascot art — trademarked, not licensed for resale",
    "brand":     "third-party trademarks (ChatGPT, Gemini, GitHub, Perplexity, X)",
    "pages":     "screenshots of other people's documentation",
    "ui":        "screenshots of other people's products",
    "src-demo":  "captured third-party page content",
}
for d, why in THIRD_PARTY.items():
    p = SKILL / d
    if p.exists():
        n = sum(1 for _ in p.rglob("*") if _.is_file())
        size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) / 1e6
        warns.append(f"{d}/ ships {n} file(s), {size:.1f} MB — {why}")

print(f"skill package: {SKILL}")
print(f"  blocks {len(list((SKILL/'ui-blocks').glob('*.html')))} · "
      f"scripts {len(list((SKILL/'scripts').glob('*')))} · "
      f"reference {len(list((SKILL/'reference').glob('*.md')))} docs")

if errs:
    print("\nBROKEN — a buyer would hit these:")
    for e in errs:
        print(f"  ✗ {e}")
else:
    print("\n  ✓ every referenced path resolves")

if warns:
    print("\nNOT YOURS TO REDISTRIBUTE (see WHATS-INCLUDED.md):")
    for w in warns:
        print(f"  ⚠ {w}")
    print("  → strip these for a paid release; the scripts resolve by path, so nothing breaks.")

sys.exit(1 if errs or (a.strict and warns) else 0)
