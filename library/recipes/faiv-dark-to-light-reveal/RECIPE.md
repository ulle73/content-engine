# Mörker → ljus (`faiv-dark-to-light-reveal`)

**FAIV · before-after · 15 s · 9:16 (4:5, 1:1 som omkomponering) · status: draft**
Maskinläsbar version: [`recipe.json`](recipe.json) (recipe/v1). Ett utgångsläge – bryt mot det när idén blir bättre.

## Idén

Världens bästa produktbevis för extraljus: samma bil, samma plats, samma stativ – ljuset av, sedan på. Tittaren
behöver ingen text för att förstå. Filmen lever på kontrasten och på att ljuset slår på **exakt på musikens drop**.

**Krok (0–2 s):** helt mörk bild, en rad text: *"Så här mörkt är det."* Ingen logga, ingen intro.

## Scen för scen

| # | Tid | Material | Regi |
|---|---|---|---|
| s1 hook | 0,0–2,0 | `fa-m1` (ljus av) | Låst stativ, låst exponering. Bilden ska kännas obekvämt mörk – lyft inte i grade. Rumston/natt-ambiens. |
| s2 spänning | 2,0–3,5 | `fa-m4` / `fa-n2` | Viltskylt som knappt syns. Riser byggs mot dropet. |
| s3 reveal | 3,5–6,0 | `fa-m1` (ljus på) | **Hårt klipp på dropet**, exakt samma utsnitt som s1. Impact + kort kameraskak (1–2 frames). Ingen text – låt bilden tala. |
| s4 bevis | 6,0–9,0 | `fa-m3` / `fa-m2` | Ljuskäglan över vägen, reflexstolpar som tänds. Text: *"Och så här ser det ut med rätt ljus."* |
| s5 produkt | 9,0–12,0 | `fa-p5` / `fa-p1` | Makro, lampan tänds i slow-mo. Produktnamn (`{product}`) från produktkatalogen. Ljussvep över produkten. |
| s6 cta | 12,0–15,0 | grafik | Logga blur-reveal, *"Montering i Kungälv · faiv.se"*. Grafit, vit, signalröd som enda accent. |

## Klipprytm

~100 BPM. Klipp på slag 1 i varje takt fram till dropet; dropet (s3) är filmens enda riktigt hårda moment – resten
andas. Håll s3 minst 2 s så ögat hinner se skillnaden. Speed ramp får användas i s4 men aldrig i s1/s3 (bevisets ärlighet).

## Text

Korta rader, max ~6 ord, `nextphase.zak.caption` (vit Inter 700, hårdklipp). Inga siffror om räckvidd, lux eller
säkerhet utan verifierat fact-id i faktabanken (`skills/faiv-fakta`). Säkra formuleringar: "Montering i Kungälv.",
"Extraljus, grillkit och arbetsljus."

## Ljud

Natt-ambiens i s1, riser i s2, **klicket (`bo-3`) + impact exakt på dropet**, motorljud under s4, swell i s5, shimmer
på loggan. Musik: originalspår via `tools.make-music` ("mörk, spänd ambient som bygger mot ett tungt drop"). Mixa till −14 LUFS
(`golfkuponger.soundtrack-mixer` fungerar för alla bolag). Filmen ska fungera utan ljud.

## AI-uppgraderingar (valfria, betalda)

| Scen | Modell | Varför |
|---|---|---|
| s2 | Kling (t2v) | Stämnings-b-roll om viltskylt i mörker saknas. |
| s5 | Kling (i2v) | Makro från **exakt produktfoto** som startbild (D12) om `fa-p5` inte filmats. |
| s1, s3, s4 | **Aldrig AI** | Ljusbilden är ett produktpåstående – AI-simulering vore vilseledande. |

Se `library/models/kling/PLAYBOOK.md` för promptformat och fallgropar.

## Varianter

- **Snö/dimma** (`fa-m2`) under mörkerperioden – dimman gör ljuskäglan synlig.
- **Split-screen** av/på i stället för klipp (övergång `hyperframes.registry.before-after-wipe`).
- **Drönare bakifrån** när ljuset slår på (Baja Designs-referensen) om drönarfilm finns.
- **Pris-slutkort** (`{fact:F5}`–`{fact:F7}`) – bara med verifierat, aktuellt pris.

## QA

Se `qa` i `recipe.json`. Viktigast: samma bil/plats/stativ i av och på, ljuset tänds på slaget, inga regskyltar, inga
overifierade påståenden.
