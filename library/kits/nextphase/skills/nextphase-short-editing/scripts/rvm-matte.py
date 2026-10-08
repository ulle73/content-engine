#!/usr/bin/env python
"""
RVM (Robust Video Matting) person segmentation -> BGRA PNG frames with alpha.

The ONLY matting approach approved for NextPhase cutouts. MediaPipe smudges hair
and the ceiling line; rembg is unreliable to install. RVM's recurrent state is what
kills frame-to-frame flicker — that temporal stability is the whole reason the
cutout reads as seamless instead of crawling.

Run inside the persistent env (see reference/cutout-compositing.md):
    source library/.venv/Scripts/activate      # Git Bash, Windows-venv (se library/kits/nextphase/SETUP.md)
    python scripts/rvm-matte.py --src in.mp4 --out /path/frames_rvm --frames 150

Every knob has a NextPhase default; you normally only pass --src/--out/--frames.
"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _win_utf8  # noqa: E402,F401  content-engine import: UTF-8 text I/O on Windows
import argparse, os, sys, time

def main():
    p = argparse.ArgumentParser(description="RVM matte a clip to BGRA PNG frames")
    p.add_argument("--src", required=True, help="source video (talking head)")
    p.add_argument("--out", required=True, help="output dir for %%05d.png BGRA frames")
    p.add_argument("--frames", type=int, default=150, help="frames to write (150 = 5s @30fps)")
    p.add_argument("--start", type=int, default=0, help="first source frame to matte")
    p.add_argument("--downsample", type=float, default=0.4,
                   help="0.4 = sharp default; 0.25 = sharper hair, slower; 0.5+ = soft")
    p.add_argument("--warmup", type=int, default=2,
                   help="throwaway passes over the first frame to prime recurrent state "
                        "(kills the first-frame flicker)")
    p.add_argument("--device", default="cpu", choices=["cpu", "cuda", "mps"],
                   help="cpu is the safe default (Windows/AMD: cpu); cuda on NVIDIA; mps on Apple")
    p.add_argument("--variant", default="mobilenetv3", choices=["mobilenetv3", "resnet50"])
    a = p.parse_args()

    import cv2, torch, numpy as np

    os.makedirs(a.out, exist_ok=True)
    model = torch.hub.load("PeterL1n/RobustVideoMatting", a.variant, trust_repo=True)
    model.eval()
    dev = torch.device(a.device)
    model = model.to(dev)

    cap = cv2.VideoCapture(a.src)
    if not cap.isOpened():
        sys.exit(f"rvm-matte: cannot open {a.src}")
    if a.start:
        cap.set(cv2.CAP_PROP_POS_FRAMES, a.start)

    def to_tensor(frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return torch.from_numpy(rgb).permute(2, 0, 1).float().unsqueeze(0).div(255.0).to(dev)

    ok, first = cap.read()
    if not ok:
        sys.exit("rvm-matte: could not read a first frame")

    # Prime the recurrent state on the first frame so frame 0 is as clean as frame 50.
    rec = [None] * 4
    with torch.no_grad():
        for _ in range(max(0, a.warmup)):
            _, _, *rec = model(to_tensor(first), *rec, downsample_ratio=a.downsample)

    frame, i, t0 = first, 0, time.time()
    with torch.no_grad():
        while i < a.frames:
            fgr, pha, *rec = model(to_tensor(frame), *rec, downsample_ratio=a.downsample)
            alpha = (pha[0, 0].cpu().numpy() * 255).clip(0, 255).astype(np.uint8)
            bgra = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)
            bgra[:, :, 3] = alpha
            cv2.imwrite(os.path.join(a.out, f"{i:05d}.png"), bgra)
            i += 1
            if i % 30 == 0:
                print(f"  {i}/{a.frames} frames  ({(time.time()-t0)/i:.2f}s/frame)", flush=True)
            ok, frame = cap.read()          # sequential only — RVM depends on frame order
            if not ok:
                break
    cap.release()
    print(f"rvm-matte: wrote {i} frames -> {a.out}  ({time.time()-t0:.0f}s total)")
    if i < a.frames:
        print(f"rvm-matte: WARNING source ran out at {i} frames (wanted {a.frames})")

if __name__ == "__main__":
    main()
