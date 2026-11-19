# Mallformatet för dashboarden (mall/v1)

Gemensamma delar för mallar som ska kunna skapas i dashboarden. Designen finns i `docs/designs/mallmotor.md`.

| Fil | Vad den gör |
| :--- | :--- |
| `mall.schema.json` | Schemat för en malls `mall.json`: reglage, gränser, format, standard per format och utdata. |
| `sida.mjs` | Sidkontraktet. Mallsidan importerar `starta()` och beskriver bara sitt utseende. |
| `render-bas.mjs` | Renderingsskelettet: lokal server, Chrome, `window.PARAMS`, väntan på `KLAR`, stillbild (JPG/PNG) eller video (ffmpeg). |
| `testmall/` | En liten bildmall som kontrollerna provas mot. Syns inte i dashboarden. |

## En mall är en mapp

```text
library/templates/<mall>/
  mall.json     reglage och gränser (enda stället där gränserna finns)
  sida.html     sidan, byggd på ../_mall/sida.mjs
  render.mjs    import { cli } from '../_mall/render-bas.mjs'; await cli(import.meta.url);
  referens/     <format>.png med standardvärdena
```

Sidan beskriver två saker:

- `forbered(v, ctx)` bygger sidan för värdena `v`. `ctx` innehåller `format`, `bredd`, `hojd` och `marginal`, det vill säga säkra marginaler från `edit-renderer/src/safezones.js`.
- `rita(t, v, ctx)` ritar tiden `t`. Samma `t` ska alltid ge samma bild, så sidan får inte använda `Math.random()` eller klockan.

En videomall returnerar dessutom `{ langd }` från `info(v, ctx)`.

Bilder och klipp kommer från R2 eller `work/` som värden (reglagetypen `bild`). De ligger aldrig i repot, eftersom repot är publikt.

## Kontrollera

```text
python library/tools/build_catalog.py --check              mall.json mot schemat och gränserna
node library/tools/kontrollera_mallar.mjs                  sidkontraktet, säkra zoner och referensbilder i Chrome
node library/tools/kontrollera_mallar.mjs --sjalvtest      dessutom: trasiga varianter av testmallen ska stoppas
node library/tools/kontrollera_mallar.mjs <mapp> --uppdatera-referens   ny referensbild (titta på den innan commit)
node library/templates/<mall>/render.mjs --lokal [--format 4x5] [--satt rubrik="Hej"] [--ut work/x]
```

Referensbilderna kommer från CI-jobbet `mallar` (Linux, Chrome). Chrome på Windows ritar textkanter lite annorlunda, så en
lokal körning kan ligga strax över gränsen på 0,5 % fast inget ändrats. Gör så här för att uppdatera en referens: kör lokalt med
`--uppdatera-referens` för att se bilden, pusha och låt CI-jobbet misslyckas. Ta sedan `<mall>-<format>.png` ur artefakten
`mallkontroll` och lägg den i `referens/<format>.png`.

En sida kan också öppnas fristående via en lokal server, med till exempel `?format=9x16&visa_zoner=1`. Då ritas plattformarnas osäkra zoner ovanpå bilden.
