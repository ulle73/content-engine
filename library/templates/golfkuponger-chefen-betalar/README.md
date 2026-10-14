# Golfkuponger – "Ingen portal? Låt chefen betala din golf" (9:16, 26,9 s)

Godkänd av Jonas 2026-10-14 (ljud M1, C1, ST1). Fräck ton: dörren märkt FÖRMÅNSPORTAL leder till en tegelvägg,
Tourleif köper direkt på golfkuponger.se i mobilen, kvittot kommer som pdf, chefen stämplar GODKÄNT, alla golfar.
Tidslinje med tider, text och ljud: `MANUS.md`.

## Ny film från mallen

```bash
cp -r library/templates/golfkuponger-chefen-betalar work/<namn>
cd work/<namn>
./make.sh            # -> out/gk-chefen-betalar-9x16.mp4
```

`fetch_assets.py` hämtar delad ritkod (årsskiftesmallen), figurerna **Tourleif** och **Chefen** från sina moduler,
loggan från den officiella filen och alla ljud ur ljudbanken. Stilbilder: `node sf-render.mjs` (→ `out/chef-sheet.png`).

## Material i mallen

| Material | Var | Om det ändras |
|---|---|---|
| Riktiga mobilskärmar från golfkuponger.se (start → paket → kassa, "Tourleif" skrivs) | `src/assets/flow/` | Sajten ändras: kör `node capture_flow.mjs` (trycker aldrig Betala, fyller bara "Tourleif") och justera `S_PK`, `S_NAME`, `S_PAY`, `PAY_Y` i `src/chef-film.js` efter `geo.json` |
| Jonas riktiga kvitto, **anonymiserat** (namn → Tourleif, adress/e-post/kortsiffror suddade, skattetexten på sida 2 borttagen) | `src/assets/kvitto-*.png` | Originalet läggs aldrig i git |

Inget gränssnitt är påhittat: mobilen visar riktiga skärmar; bocken, mejlnotisen och det tecknade kvittot på chefens
bord är våra egna illustrationer.

## Återanvändbara delar

| Del | Var |
|---|---|
| Dörr som öppnas mot tegelvägg + spindelnät ("här finns inget") | `src/chef-film.js` `partDoor`, `bricks`, `cobweb` |
| **Mobilflöde med riktiga skärmar**: kameran följer fingret, mjuk scroll, sidbyte, skrivande, zoom, panorering | `src/chef-film.js` `partPhone`, `phoneScreen`, `tap` |
| Stor grön bock som ritas fram (tack-sida) + mejlnotis med pdf | `phoneScreen` (9,6–11 s) |
| Kontor med chefen, skrivbord, namnskylt; kvitto som glider fram och läses | `src/chef.js` `office`; `partOffice` |
| **GODKÄNT-stämpel** som slår ner (spegelbild av förbudsmärket) | `src/chef.js` `stamp` |
| Figurer | `golfkuponger.character.tourleif`, `golfkuponger.character.chefen` |

## Fakta (F2, bekräftad av Jonas 2026-10-13)

Vem som helst kan köpa direkt på golfkuponger.se; kvittot kommer som pdf på mejlen och kan användas som underlag för
friskvårdsbidrag hos arbetsgivaren. Rak text godkänd: "Låt chefen betala din golf".
