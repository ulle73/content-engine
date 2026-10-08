---
name: studio
description: Ingången för allt innehåll som ska skapas – video, reels, annonser, karuseller, animationer, motion graphics, explainers, musikvideor, bilder och copy. Använd ALLTID först, innan något byggs från noll. Söker i Content Library (library/catalog.json) efter färdiga, snygga och verifierade mallar, effekter, övergångar, textbehandlingar, karusellstilar, skills och prompts, föreslår 2–3 kombinationer med förhandsvisning och anpassar sedan det valda till det användaren vill ha.
---

# Studio – börja alltid från något snyggt

Allt nytt innehåll börjar i biblioteket. Vi bygger aldrig från noll när det finns en färdig mall,
effekt eller stil som kan anpassas. Det finns inga stilregler här: allt får användas och
kombineras – glitch, whips, 3D, morphs, hårda klipp, studs, vilka typsnitt och hur mycket text
som helst. Brand-skillen (`golfkuponger-brand`) är ett **utgångsläge**, inte en spärr.

## 1. Förstå beställningen (max 3 frågor, alltid med förslag)

Fråga bara det som saknas: vad (video, karusell, bild …), var den ska gå (format: 9:16 / 1:1 /
4:5 / 16:9), längd, känsla eller en referens ("som den här videon"), och vilket material som
finns (bilder, logga, skärminspelningar, musik). En referens lyfter resultatet mest – be om en.

## 2. Sök i biblioteket

```bash
python library/tools/build_catalog.py          # om catalog.json saknas eller är gammal
python library/tools/find.py "<ord från beställningen>" --format 9:16 --limit 20
python library/tools/find.py "<ord>" --type template --verified
python library/tools/find.py "<ord>" --type transition
```

Sök flera gånger: en **bas** (`template`, `carousel` eller en `skill`), **effekter/övergångar**
(`effect`, `transition`, `background`, `grade`), **text** (`text`, `caption`), **ljud** (`sound`)
och **prompts** (`prompt`, t.ex. regissörsbrief och kritikloop). Bläddra visuellt i
`library/gallery.html`. Verifierade poster med förhandsvisning går först.

## 3. Föreslå 2–3 kombinationer

Varje förslag: basmall + 2–4 effekter/övergångar + textbehandling + ljud, med id:n och
förhandsvisningar (`library/previews/…`). Säg varför de passar. Låt användaren välja eller
blanda. Ingen beställning ska få samma tre förslag – variera stil på riktigt.

## 4. Bygg från det valda

Varje post har `use` som säger hur den körs: en skill (`/live-carousel`, `/animate`,
`/motiongraphics`, `/carousel-kit`, `/persa-short-editing`, `/motion-studio`, `/hyperframes` …),
ett komponentblock att kopiera in, eller en prompt att fylla i. Arbetsfiler och renderingar
läggs i `work/` (inte i git). Golfkuponger-material: `skills/golfkuponger-brand` (färger,
typsnitt, logga, bildspråk som utgångsläge) och `skills/golfkuponger-friskvard` (köpvägar,
vinklar och faktabank).

**Fakta:** påståenden i reklam ska komma från faktabanken (`golfkuponger-friskvard`). Säg till
om något är overifierat.

## 5. Kritikloop innan leverans

Rendera en kontaktkarta (en bild per beat), en mobilvy (~360 px bred) och strip runt snabba
moment. Titta på dem. Sätt poäng 1–10 på: krok första 2 s, läsbarhet på mobil, rörelsekvalitet,
variation (något nytt var 2–4 s), komposition, varumärke, ljudsynk. Fixa de tre sämsta, upprepa
tills allt är 8+. Mall: `library/prompts/motion-studio-playbook/` (kritikloop).

## 6. Låt biblioteket växa

Blev resultatet bra: spara det som ny mall i `library/templates/<namn>/` med förhandsvisning
och en post i `LIBRARY.json` (`status: verified`), kör `build_catalog.py`. Nästa gång börjar
någon därifrån.
