"""Hämta en referensvideo (Instagram, TikTok, YouTube, Facebook, direktlänk) för att bryta ner den till tekniker.

  .venv/Scripts/python.exe -I library/techniques/hamta.py <länk>

Skriver till work/references/<plattform>-<id>/ (lokalt, aldrig i git – videon är kreatörens):
  video.mp4, meta.json (kreatör, likes, kommentarer, visningar, datum, längd, beskrivning),
  kontaktark.png (en bild var 0,67 s med tid), klipp.txt (bildbyten med tider), klipp-*.png (en bild per klipp).
Karusell (flera bilder/klipp i ett inlägg): slide-NN.jpg / slide-NN.mp4 (+ slide-NN-kontakt.png per klipp),
kontaktark.png med alla slides i ordning och meta.json med antal slides.
Sedan: titta på kontaktarket och klippbilderna och lägg in teknikerna enligt skills/teknik.
"""
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def datum(info):
    d = info.get("upload_date")
    if d:
        return f"{d[:4]}-{d[4:6]}-{d[6:8]}"
    ts = info.get("timestamp")
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d") if ts else None


def meta_av(info, url, plat, vid):
    return {"länk": url, "plattform": plat, "id": vid, "kreatör": info.get("uploader") or info.get("channel"),
            "konto": info.get("channel") or info.get("uploader_id"), "likes": info.get("like_count"),
            "kommentarer": info.get("comment_count"), "visningar": info.get("view_count"),
            "datum": datum(info),
            "beskrivning": (info.get("description") or info.get("title") or "")[:1500]}


def karusell(info, entries, url, out, plat, vid):
    import yt_dlp
    slides = []
    for i, e in enumerate(entries, 1):
        bas = os.path.join(out, f"slide-{i:02d}")
        if e.get("formats"):
            if not os.path.exists(bas + ".mp4"):
                with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "noprogress": True,
                                       "format": "best[ext=mp4]/bv*+ba/best", "merge_output_format": "mp4",
                                       "outtmpl": bas + ".%(ext)s"}) as y:
                    y.process_ie_result(dict(e), download=True)
            dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                        bas + ".mp4"], capture_output=True, text=True).stdout.strip() or 0)
            ffmpeg("-i", bas + ".mp4", "-vf", "fps=2,scale=220:-1,drawtext=text='%{pts\:hms}':x=4:y=4:fontsize=16:"
                   "fontcolor=white:box=1:boxcolor=black@0.6,tile=8x4", "-frames:v", "1", bas + "-kontakt.png")
            ffmpeg("-ss", "0.3", "-i", bas + ".mp4", "-frames:v", "1", bas + ".jpg")
            slides.append({"slide": i, "typ": "video", "längd_s": round(dur, 2)})
        else:
            th = sorted(e.get("thumbnails") or [], key=lambda t: (t.get("width") or 0) * (t.get("height") or 0))
            if not os.path.exists(bas + ".jpg") and th:
                req = urllib.request.Request(th[-1]["url"], headers=e.get("http_headers") or {})
                with urllib.request.urlopen(req, timeout=60) as r, open(bas + ".jpg", "wb") as f:
                    f.write(r.read())
            slides.append({"slide": i, "typ": "bild"})
    meta = meta_av(info, url, plat, vid) | {"format": "karusell", "slides": slides}
    json.dump(meta, open(os.path.join(out, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    ins = []
    for s in slides:
        ins += ["-i", os.path.join(out, f"slide-{s['slide']:02d}.jpg")]
    n = len(slides)
    cols = min(n, 5)
    rows = (n + cols - 1) // cols
    lay = "|".join(f"{(k % cols) * 360}_{(k // cols) * 450}" for k in range(n))
    vf = ";".join(f"[{k}:v]scale=360:450:force_original_aspect_ratio=decrease,pad=360:450:(ow-iw)/2:(oh-ih)/2,"
                  f"drawtext=text='{k + 1}':x=6:y=6:fontsize=28:fontcolor=white:box=1:boxcolor=black@0.6[s{k}]"
                  for k in range(n))
    vf += ";" + "".join(f"[s{k}]" for k in range(n)) + (f"xstack=inputs={n}:layout={lay}:fill=black" if n > 1 else "copy")
    ffmpeg(*ins, "-filter_complex", vf, "-frames:v", "1", os.path.join(out, "kontaktark.png"))
    print(json.dumps({k: v for k, v in meta.items() if k != "beskrivning"}, ensure_ascii=False))
    print(f"karusell: {n} slides ({sum(s['typ'] == 'video' for s in slides)} videoklipp)")
    print("mapp:", out)


def main(url):
    import yt_dlp
    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True,
                           "ignore_no_formats_error": True}) as y:
        info = y.extract_info(url, download=False, process=False)
    plat = re.sub(r"[^a-z]", "", (info.get("extractor_key") or info.get("ie_key") or "video").lower())[:12]
    vid = re.sub(r"[^A-Za-z0-9_-]", "", str(info.get("id") or "video"))[:40]
    out = os.path.join(ROOT, "work", "references", f"{plat}-{vid}")
    os.makedirs(out, exist_ok=True)
    entries = list(info.get("entries") or [])
    if info.get("_type") == "playlist" and entries:
        return karusell(info, entries, url, out, plat, vid)
    video = os.path.join(out, "video.mp4")
    if not os.path.exists(video):
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "noprogress": True, "format": "best[ext=mp4]/best", "outtmpl": video}) as y:
            y.download([url])
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                               capture_output=True, text=True).stdout.strip() or 0)
    meta = meta_av(info, url, plat, vid) | {"längd_s": round(dur, 2)}
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
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1])
