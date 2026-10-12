import glob, sys, os
from PIL import Image, ImageDraw
files = sorted(glob.glob('build/still_*.png'))
sel = sys.argv[2:] if len(sys.argv) > 2 else None
if sel: files = [f for f in files if any(s in f for s in sel)]
tw, th, cols = 300, 533, 6
rows = (len(files) + cols - 1) // cols
sheet = Image.new('RGB', (cols * tw, rows * (th + 24)), (40, 40, 40))
d = ImageDraw.Draw(sheet)
for i, f in enumerate(files):
    im = Image.open(f).resize((tw, th), Image.LANCZOS)
    x, y = (i % cols) * tw, (i // cols) * (th + 24)
    sheet.paste(im, (x, y + 24)); d.text((x + 6, y + 5), os.path.basename(f)[6:-4] + ' s', fill='yellow')
sheet.save(sys.argv[1])
