# bgm/ — bädden (borttagen)

Originalet `house-bed-loop.m4a` var en 36 s loop ur en **kommersiell låt** (namngiven artist) —
licens för att använda den i egna videor är inte licens att sprida den, så den togs bort vid importen.

Lägg en egen, rättighetsklar instrumental loop här som `house-bed-loop.m4a` (≈36 s, nivå ≈ -34 LUFS),
eller ge sökvägen direkt:

```bash
bash library/kits/nextphase/skills/nextphase-short-editing/scripts/lay-bed.sh in.mp4 ut.mp4 path/till/bed.m4a
```

Gratisväg: generera loopen lokalt med ACE-Step (CPU, gratis) eller använd en Pixabay-låt
(Pixabay Content License). Nivå: mät med `ffmpeg -af ebur128` och sikta på -34 LUFS.
