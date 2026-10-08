"""Compare music candidates: beat grid (beat_grid.py) + per-0.5 s loudness (RMS, sub-150 Hz, >4 kHz)."""
import json, subprocess, sys
import numpy as np

PY = sys.executable
BG = "library/prompts/motion-studio-playbook/beat_grid.py"
for name in sys.argv[1:]:
    wav = f"work/friskvard-v2/music/{name}.wav"
    out = f"work/friskvard-v2/scratch/beats-{name}.json"
    subprocess.run([PY, BG, wav, "--fps", "30", "--out", out], check=True, capture_output=True)
    d = json.load(open(out))
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", wav, "-ac", "1", "-ar", "22050", "-f", "f32le", "-"],
                         capture_output=True).stdout
    y = np.frombuffer(raw, np.float32); sr = 22050; n = sr // 2
    print(f"== {name}: bpm {d['bpm']:.2f}  drop {d.get('drop')}  dur {len(y)/sr:.1f}s")
    print("   downbeats", [round(x, 2) for x in d["downbeats"]])
    print("   hits", [(round(h['t'], 2), round(h['strength'], 2)) for h in d["hits"]][:30])
    line = []
    for i in range(len(y) // n):
        s = y[i*n:(i+1)*n]; sp = np.abs(np.fft.rfft(s)); fr = np.fft.rfftfreq(len(s), 1/sr)
        rms = 20*np.log10(np.sqrt((s**2).mean()) + 1e-9)
        low = 20*np.log10(np.sqrt((sp[fr < 150]**2).sum())/len(s) + 1e-9)
        line.append(f"{i*0.5:4.1f}:{rms:5.1f}/{low:5.1f}")
    for k in range(0, len(line), 10):
        print("   " + "  ".join(line[k:k+10]))
