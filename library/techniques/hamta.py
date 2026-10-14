"""Hämta en referensvideo (Instagram, TikTok, YouTube, Facebook, direktlänk) för att bryta ner den till tekniker.

  python -I library/techniques/hamta.py <länk>

Skriver till work/references/<plattform>-<id>/ (lokalt, aldrig i git – videon är kreatörens):
  video.mp4, meta.json (kreatör, likes, kommentarer, visningar, datum, längd, beskrivning),
  kontaktark.png (en bild var 0,67 s med tid), klipp.txt (bildbyten med tider), klipp-*.png (en bild per klipp).
Sedan: titta på kontaktarket och klippbilderna och lägg in teknikerna enligt skills/teknik.
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def main(url):
    import yt_dlp
    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True}) as y:
        info = y.extract_info(url, download=False)
    plat = re.sub(r"[^a-z]", "", (info.get("extractor_key") or "video").lower())[:12]
    vid = re.sub(r"[^A-Za-z0-9_-]", "", str(info.get("id") or "video"))[:40]
    out = os.path.join(ROOT, "work", "references", f"{plat}-{vid}")
    os.makedirs(out, exist_ok=True)
    video = os.path.join(out, "video.mp4")
    if not os.path.exists(video):
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "noprogress": True, "format": "best[ext=mp4]/best", "outtmpl": video}) as y:
            y.download([url])
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                               capture_output=True, text=True).stdout.strip() or 0)
    meta = {"länk": url, "plattform": plat, "id": vid, "kreatör": info.get("uploader") or info.get("channel"),
            "konto": info.get("channel") or info.get("uploader_id"), "likes": info.get("like_count"),
            "kommentarer": info.get("comment_count"), "visningar": info.get("view_count"),
            "datum": info.get("upload_date") or info.get("timestamp"), "längd_s": round(dur, 2),
            "beskrivning": (info.get("description") or "")[:1500]}
    json.dump(meta, open(os.path.join(out, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    # kontaktark med tidsstämplar
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vf",
                    "fps=1.5,scale=220:-1,drawtext=text='%{pts\\:hms}':x=4:y=4:fontsize=16:fontcolor=white:box=1:boxcolor=black@0.6,tile=8x6",
                    "-frames:v", "1", os.path.join(out, "kontaktark.png")], check=True)
    # bildbyten (klipp) och en bild per klipp
    r = subprocess.run(["ffmpeg", "-i", video, "-vf", "select='gt(scene,0.28)',showinfo", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="ignore")
    cuts = [0.0] + [float(x) for x in re.findall(r"pts_time:([0-9.]+)", r.stderr)]
    with open(os.path.join(out, "klipp.txt"), "w", encoding="utf-8") as f:
        for i, t in enumerate(cuts):
            nxt = cuts[i + 1] if i + 1 < len(cuts) else dur
            f.write(f"klipp {i + 1:02d}: {t:6.2f}–{nxt:6.2f} s ({nxt - t:4.2f} s)\n")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{min(dur - 0.05, t + min(0.4, (nxt - t) / 2)):.2f}", "-i", video,
                            "-frames:v", "1", "-vf", "scale=360:-1", os.path.join(out, f"klipp-{i + 1:02d}.png")])
    print(json.dumps({k: v for k, v in meta.items() if k != "beskrivning"}, ensure_ascii=False))
    print(f"{len(cuts)} klipp, snitt {dur / max(1, len(cuts)):.2f} s per klipp")
    print("mapp:", out)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1])
