"""Soundtrack = music (assets/music.wav, ACE-Step track F, 25.0 s) + SFX bus (assets/audio/sfx.wav from build_sfx.py),
two-pass loudnorm to -14 LUFS integrated, true peak <= -1 dBTP -> assets/soundtrack.wav. Run from the project root:
    python audio/make_cues.py
    python <repo>/.claude/skills/motion-studio/scripts/sfx/build_sfx.py .
    python audio/mix.py
"""
import json, re, subprocess, sys

SFX_DB = float(sys.argv[1]) if len(sys.argv) > 1 else -7.0
MUSIC_DB = 0.0
pre = (f"[0:a]aresample=48000,volume={MUSIC_DB}dB[m];[1:a]aresample=48000,volume={SFX_DB}dB[s];"
       f"[m][s]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.89:attack=3:release=60:level=disabled[x]")
# pass 1: measure
r = subprocess.run(["ffmpeg", "-hide_banner", "-i", "assets/music.wav", "-i", "assets/audio/sfx.wav", "-filter_complex",
                    pre + ";[x]loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json[o]", "-map", "[o]", "-f", "null", "-"],
                   capture_output=True, text=True)
m = json.loads(re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr)[-1])
ln = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
      f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", "assets/music.wav", "-i", "assets/audio/sfx.wav",
                "-filter_complex", pre + f";[x]{ln},aresample=48000,atrim=0:25.0[o]", "-map", "[o]", "-c:a", "pcm_s16le",
                "assets/soundtrack.wav"], check=True)
r = subprocess.run(["ffmpeg", "-hide_banner", "-i", "assets/soundtrack.wav", "-af", "ebur128=peak=true", "-f", "null", "-"],
                   capture_output=True, text=True)
s = r.stderr[r.stderr.rfind("Summary"):]
print("I:", re.search(r"I:\s+(-?[\d.]+) LUFS", s).group(1), "LUFS   TP:", re.search(r"Peak:\s+(-?[\d.]+) dBFS", s).group(1), "dBTP")
