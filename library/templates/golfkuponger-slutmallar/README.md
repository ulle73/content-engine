# Slutmallar med svingloggan

Slutscen för Golfkupongers filmer: den rörliga svingloggan (Spotlight-outron) och sedan två textrader och portalerna
på mörkgrönt. Beställd av Jonas 2026-11-16.

## Mallar

| mall | visar |
|---|---|
| `alla` | alla portalkort på en rad |
| `epassi` | Epassi-kortet + "Sök Golfkuponger i Epassi" |
| `benify` | Benifex-kortet (Benify heter Benifex i loggan) + "Sök Golfkuponger i Benifex" |
| `sp` | Söderberg & Partners |
| `edenred` | Edenred |

## Text

- **Rad 1** – liten guldfärgad överrubrik i versaler, högst 40 tecken. Får vara tom.
- **Rad 2** – stor rubrik i versaler, högst 48 tecken. Skriv `*ord*` för att göra ord guldfärgade, t.ex.
  `Det brinner inne *31/12*`.
- Texten mäts in efter att typsnitten laddats, så den krymper i stället för att gå utanför bilden.
- Påståenden (antal banor, priser, datum) ska komma ur faktabanken (`skills/golfkuponger-friskvard`).

## Rendera lokalt

```bash
node library/templates/golfkuponger-slutmallar/render.mjs --mall alla --rad1 "Friskvårdsbidrag kvar?" --rad2 "Det brinner inne *31/12*" --ut work/<film>/slut --format 9x16,4x5
```

Eller med en jobbfil: `node render.mjs --json jobb.json` där filen är
`{ "mall", "rad1", "rad2", "ut", "format": ["9x16", "4x5"] }`.

Ut: `<ut>/slutmall-<mall>-<format>.mp4` och ett kontaktark `kontakt-<mall>-<format>.jpg`. Sista raden på stdout är
JSON med filerna och längden. Kräver Node, ffmpeg och Playwright i `work/animate` (via
`.claude/skills/animate/tools/pw.mjs`, som kör systemets Chrome). Längd: ca 7,7 s för `alla`, ca 6,9 s för en portal.

## I dashboarden

Generera video → Typ av video: **Slutmall**. Välj mall, skriv rad 1 och rad 2 (förhandsvisningen visar texten) och
klicka Skapa film. Jobbet renderas av GitHub-workflowen `sms-film-render.yml` (samma kö som SMS-filmerna) och
hamnar under Dina filmer. Filmen blir 9:16 med ljud.

## Filer

- `slutmall.html` – scenen; läser `?mall=&r1=&r2=&h=` och exponerar `window.frame(t)` och `window.INFO`.
- `render.mjs` – tar bildrutor och lägger ihop dem med svingloggans ljud.
- `assets/` – typsnitt (Anton, Inter), GK-logga och portalloggor.
