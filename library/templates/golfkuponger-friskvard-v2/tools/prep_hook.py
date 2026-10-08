"""Hook plate layers from the 3x Österåker crop (film/assets/hook-plate.jpg):
  hook-sky.jpg     clean sky plate (tree region filled by stretching the sky column-wise) for cinemagraph drift
  hook-fg.png      trees + fairway (luma-keyed sky removed) — sits over the drifting sky
  hook-golfer.png  the golfer cutout (from `npx hyperframes remove-background`)
"""
import numpy as np
from PIL import Image, ImageFilter

A = "work/friskvard-v2/film/assets/"
from PIL import ImageFilter as _F
src = Image.open(A + "klubb-osteraker-gk.jpg").convert("RGB")
# big plate: source crop (0,120)-(760,941) at 3x -> 2280x2463; every format frames a window of it
im = src.crop((0, 120, 760, 941)).resize((2280, 2463), Image.LANCZOS).filter(_F.UnsharpMask(2, 60, 2))
im.save(A + "hook-plate.jpg", quality=92)
a = np.asarray(im).astype(np.float32) / 255
H, W, _ = a.shape
luma = a @ np.array([0.2126, 0.7152, 0.0722])
sat = a.max(2) - a.min(2)
sky = ((luma > 0.62) & (sat < 0.28)).astype(np.float32)
# keep only the sky connected to the top: per column, sky until the first long run of non-sky
mask = np.zeros_like(sky)
for x in range(W):
    col = sky[:, x]
    miss = 0
    for y in range(H):
        if col[y] > 0.5:
            mask[y, x] = 1; miss = 0
        else:
            miss += 1
            if miss > 6:
                break
mask[int(H * 0.62):] = 0  # never below the fairway line
# boundary per column, smoothed, then a soft luma key inside a band around it (keeps leaf detail)
bound = np.array([np.where(mask[:, x] > 0)[0].max() if mask[:, x].any() else 0 for x in range(W)], np.float32)
k = 15
pad = np.pad(bound, k, mode="edge")
bound_s = np.array([np.median(pad[i:i + 2 * k + 1]) for i in range(W)])
yy = np.arange(H)[:, None]
soft = np.clip((luma - 0.46) / 0.14, 0, 1) * np.clip((0.46 - sat) / 0.12, 0, 1)
band_top = bound_s[None, :] - 60
band_bot = bound_s[None, :] + 160
mask = np.where(yy < band_top, 1.0, np.where(yy > band_bot, 0.0, soft))
m = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
# matte for foreground = inverse sky
fg = im.copy(); fg.putalpha(Image.fromarray(255 - np.asarray(m)))
fg.save(A + "hook-fg.png")
# clean sky: for each column, take the sky colour just above the boundary and extend downwards
sk = a.copy()
mk = np.asarray(m).astype(np.float32) / 255
for x in range(W):
    ys = np.where(mk[:int(H*0.62), x] > 0.9)[0]
    last = ys.max() if len(ys) else 0
    ref = a[max(0, last - 12):last + 1, x].mean(0) if len(ys) else a[0, x]
    sk[last + 1:, x] = ref
skimg = Image.fromarray((sk * 255).clip(0, 255).astype(np.uint8))
# soften the filled area horizontally so column streaks vanish
blur = skimg.filter(ImageFilter.BoxBlur(60)).filter(ImageFilter.GaussianBlur(30))
comp = Image.composite(skimg, blur, Image.fromarray((np.clip(mk * 1.0, 0, 1) * 255).astype(np.uint8)))
comp.save(A + "hook-sky.jpg", quality=92)
import subprocess, os
# matting works best on a tight, person-sized crop (the full plate loses the bag)
BOX = (360, 1000, 1140, 1780)
im.crop(BOX).save("work/friskvard-v2/scratch/golfer-crop.png")
subprocess.run("npx hyperframes remove-background ../scratch/golfer-crop.png -o ../scratch/hook-golfer-raw.png", shell=True, check=True, cwd="work/friskvard-v2/film", capture_output=True)
gc = Image.open("work/friskvard-v2/scratch/hook-golfer-raw.png").convert("RGBA")
# choke the matte ~2 px so the dark tree fringe around the head does not show against the type
al = gc.getchannel("A").filter(ImageFilter.MinFilter(5)).filter(ImageFilter.GaussianBlur(1.0))
gc.putalpha(al)
g = Image.new("RGBA", im.size, (0, 0, 0, 0)); g.paste(gc, BOX[:2])
ga = np.asarray(g)[:, :, 3]; ys, xs = np.where(ga > 128); print("golfer bbox", xs.min(), xs.max(), ys.min(), ys.max())
g.save(A + "hook-golfer.png")
vis = Image.new("RGB", (W, H)); vis.paste(Image.fromarray((mask * 255).astype(np.uint8)).convert("RGB"))
vis.resize((W // 3, H // 3)).save("work/friskvard-v2/scratch/hook-skymask.jpg")
comp.resize((W // 3, H // 3)).save("work/friskvard-v2/scratch/hook-sky-small.jpg")
print("ok", mask.mean())
