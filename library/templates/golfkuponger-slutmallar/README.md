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

Med effekt och egna storlekar/mellanrum:

```bash
node library/templates/golfkuponger-slutmallar/render.mjs --mall alla --eff studs --stil "logga=130,luft_logga=40,ikoner=120" --ut work/<film>/slut
```

Eller med reglagens nycklar (se `mall.json`): `node render.mjs --lokal --satt text2="Det brinner inne *31/12*" --satt effekt=studs --satt logga=130`.

Jobbfil: `node render.mjs --json jobb.json` med `{ "varden": { "mall": "alla", "text1": "…", "text2": "…", "effekt": "studs", "logga": 130 }, "format": ["9x16"], "ut": "…" }`.
Den äldre formen `{ "mall", "rad1", "rad2", "effekt", "stil": { "logga": 130 }, "ut", "format": ["9x16", "4x5"] }` fungerar också (`dashboard-worker.mjs` använder den).

### Effekter (`--eff`, `effekt`)

| Nyckel | Namn | Hur texten landar |
|---|---|---|
| `small` | Smäll (standard) | Ord för ord: slår in stort och oskarpt, krymper på plats, skakning |
| `studs` | Studs | Ord för ord: poppar upp med fjädring och ett litet hopp, lätt skakning |
| `tona` | Tona in | Ord för ord: tonar fram ur oskärpa och glider upp en bit |
| `glid` | Glid upp | Ord för ord: glider upp bakom en osynlig kant |
| `skriv` | Skrivmaskin | Bokstav för bokstav |
| `avtack` | Avtäck | Ord för ord: avtäcks från vänster till höger |

### Storlekar och mellanrum (`--stil`, `stil`)

Alla är valfria; utelämnade värden ger standardlayouten. Värden utanför spannet klämms in.

| Nyckel | Vad | Spann | Standard |
|---|---|---|---|
| `logga` | Loggans storlek | 50–160 % | 100 |
| `ikoner` | Portalikonernas storlek | 50–160 % | 100 |
| `rad1` | Rad 1 (överrubrik) | 50–160 % | 100 |
| `rubrik` | Rad 2 (rubrik) | 50–160 % | 100 |
| `cta` | "Sök Golfkuponger i …" | 50–160 % | 100 |
| `bredd` | Textens maxbredd | 560–950 px | 778 |
| `hojd` | Flytta allt upp/ner | −120–300 px | 0 |
| `luft_logga` | Luft under loggan | −30–240 px | 0 |
| `luft_rad1` | Luft under rad 1 | −30–160 px | 0 |
| `luft_rubrik` | Luft under rubriken | −20–160 px | 0 |
| `luft_cta` | Luft ovanför ikonerna | −20–200 px | 0 |
| `luft_ikoner` | Luft mellan ikonerna | −8–60 px | 0 |
| `tempo` | Effektens tempo | 50–200 % | 100 |
| `skak` | Skakning vid landning | 0–200 % | 100 för Smäll, 40 för Studs, annars 0 |

Nycklarna, spannen och standardvärdena står i `mall.json` (schemat `mall/v1`, se `library/templates/_mall/README.md`). Fram till steg 3 i `docs/designs/mallmotor.md` finns en kopia kvar i `engine/smsfilm/spec.py` (`SLUTMALL_STIL`).

Ut: `<ut>/golfkuponger-slutmallar-<format>.mp4` och ett kontaktark `kontakt-<mall>-<format>.jpg`. Sista raden på stdout är
JSON med filerna och längden. Kräver Node, ffmpeg och Playwright i `work/animate` (via
`.claude/skills/animate/tools/pw.mjs`, som kör systemets Chrome). Längd: från 3,1 s, beroende på text, effekt och tempo.

## I dashboarden

Generera video → Typ av video: **Slutmall**. Välj mall och effekt, skriv rad 1 och rad 2 och dra i reglagen för
storlek, mellanrum, placering och rörelse. Förhandsvisningen till höger är själva mallen (samma `slutmall.html`, i en
iframe via `sms-film/mall/golfkuponger-slutmallar/…`) och uppdateras direkt; **Spela upp** visar effekten, safe zones kan slås av och på,
och varningar visas om något hamnar utanför. Dubbelklicka på ett reglage för att återställa det, eller använd
"Återställ storlekar och mellanrum". Klicka Skapa film. Jobbet renderas av GitHub-workflowen `sms-film-render.yml` (samma kö som SMS-filmerna) och
hamnar under Dina filmer. Filmen blir 9:16 med ljud.

## Filer

- `mall.json` – reglagen, gränserna och standardvärdena (skakningens standard beror på effekten, `standard_per`).
- `slutmall.html` – scenen. Följer sidkontraktet (`library/templates/_mall/sida.mjs`): värdena kommer i `window.PARAMS`,
  `window.frame(t)` ritar och `window.INFO` har längd, textmått, loggans läge och varningar. De säkra zonerna läses ur
  `edit-renderer/src/safezones.js`. De äldre adressparametrarna `?mall=&r1=&r2=&h=&eff=&s_<nyckel>=` (plus `logga=1`,
  `zoner=1` och `slut=1`) fungerar fortfarande i förhandsvisningen.
- `render.mjs` – bygger på `_mall/render-bas.mjs` och lägger på svingloggan och dess ljud i ffmpeg.
- `referens/` – referensbilder (standardvärdena, mitt i filmen) som `library/tools/kontrollera_mallar.mjs` jämför med.
- `assets/` – typsnitt (Anton, Inter), GK-logga och portalloggor.
