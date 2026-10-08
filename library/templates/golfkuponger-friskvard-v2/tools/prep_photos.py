"""2x Lanczos + light unsharp pre-upscale of the course photos (Chrome's own scaler is softer)."""
from PIL import Image, ImageFilter
A = "work/friskvard-v2/film/assets/"
for n in ["hero-skogsbana", "klubb-bro-hof-slott", "klubb-halmstad-gk", "klubb-falsterbo-gk", "klubb-osteraker-gk", "anvnd-friskvrdsbidraget-till-golf"]:
    im = Image.open(A + n + ".jpg").convert("RGB")
    up = im.resize((im.width * 2, im.height * 2), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2.2, 55, 2))
    up.save(A + n + "@2x.jpg", quality=90, optimize=True)
    print(n, up.size)
