# Kontoret → banan (`gk-office-to-course-match-cut`)

**Golfkuponger · match-cut · 15 s · 9:16 (4:5, 1:1) · status: draft** · [`recipe.json`](recipe.json)

## Idén

Tre match cuts där samma rörelse fortsätter från kontoret till golfbanan: kaffekoppen blir klubban, laptopen som stängs blir
bagageluckan som öppnas, kontorsdörren blir första tee. Hela budskapet utan ord – och match cuts är tillfredsställande att se om.

**Krok:** *"Måndag 09:12"* → hårt match cut → *"Fredag 16:30"*. Första klippet sker redan vid 1,5 s.

## Scen för scen

| # | Tid | Material | Regi |
|---|---|---|---|
| s1 hook | 0–1,5 | `gk-o1` (kontor) | Lyfter kaffekoppen, låst utsnitt. |
| s2 match | 1,5–3 | `gk-o1` (bana) | Lyfter klubban – samma utsnitt, klipp i toppfart (`cut-the-curve`). |
| s3–s4 | 3–7 | `gk-o2` | Stänger laptopen → öppnar bagageluckan (push-through match cut). |
| s5–s6 | 7–11 | `gk-o3` | Går ut genom kontorsdörren → kliver ut på första tee (samma riktning), ljusläcka. |
| s7 payoff | 11–13 | `gk-g1` | Slow-mo-utslag på dropet. *"Ditt friskvårdsbidrag. Din bana."* Varm grade. |
| s8 cta | 13–15 | grafik | *"Gör ditt friskvårdsbidrag till golf."* |

## Klipprytm

~124 BPM. Paren blir snabbare: 1,5 + 1,5 s, sedan 2 + 2, 2 + 2 – stegringen bygger mot dropet i s7. Klipp alltid i
rörelsens toppfart så att ögat följer handen över klippet.

## Inspelning (viktigast)

Samma person, samma kläder (eller medvetet byte), **samma utsnitt, höjd, riktning och tempo** i båda miljöerna. Markera
kamerapositionen; filma 1 s före och efter rörelsen. Gärna stativ.

## Text och ljud

Tidsstämplar (Måndag/Fredag) som enkla etiketter; inga faktapåståenden. Whoosh på varje matchklipp, kontorsljud → fågelsång.

## AI-uppgraderingar

- **s2:** gpt-image-2 redigerar sista kontorsbilden ("change only the environment and the object in the hand") → Seedance
  animerar med samma utsnitt. Se `library/models/seedance/PLAYBOOK.md` exempel 4.
- **s6:** Kling gör tee-scenen från en startbild om banfilmen saknas.

## Varianter

- Fyra par i stället för tre (skor: kontorsskor → golfskor).
- Omvänd: golfen först, sedan "tillbaka på måndag" – med CTA om att planera nästa säsong.
- Kollegor: samma rörelse av tre olika personer.
