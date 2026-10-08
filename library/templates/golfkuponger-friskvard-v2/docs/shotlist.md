# Friskvård v2 – shotlist (låst mot musiken)

**Musik:** `music/track-f.wav` (ACE-Step, genererad med sektionstaggar [Intro][Build-up][Drop][Chorus][Outro], 120 BPM begärt).
Uppmätt: kick på varje halvsekund 0.0 → 23.5 → **120 BPM, slag = 0,500 s, takt = 2,000 s** (beat_grid.py gissade 117,45 –
fel; kickarna i 0,1 s-loudnesskurvan ligger exakt på 0,5 s-rutnätet, nedslag 0, 2, 4 … 16 … 24).
Form: tät intro 0–2,2 s → glesare vers 2,7–15,9 → **lyft/drop 16,0 s** (hi-hats + full kick, +5 dB) → slutackord 24,0 s
med klang som klingar av till ~25,2 s. Filmen = spåret från 0,0, längd **25,0 s** (750 rutor @30 fps).

Varför F och inte A/B (de beställda): A (”120 BPM pop”) mätte 117/120 men är stabbig med tystnader var 2:a takt och faller
ihop till ett break utan bas vid 17 s – inget slut. B (”100 BPM sports”) har topp vid 0,5 s och 10 s och tonar sedan ut –
ingen uppbyggnad, inget slutackord. C/D/E/G (nya försök) saknade antingen drop (C, G) eller hade dropet för sent och
för kort (E: drop 16,2 s men bara 7 s energi). F har kraftig öppning för kroken, stadig 4/4 under produkten, ett tydligt
lyft exakt där beviset (300+) ska slå och ett riktigt slutackord.

| # | Scen | Tid (s) | Slag | Händelser (exakta) |
|---|---|---|---|---|
| 1 | Krok | 0,00–3,00 | 1–6 | 0,00 **DIN CHEF** slår in (mitt i slaget redan på ruta 0) · 1,00 **BETALAR** · 2,00 **DIN GOLF.** (guld, extrudering poppar) · kamerapush + kick per ord · himlen driver (cinemagraph) · golfaren friläggs framför texten |
| 2 | Vändning | 3,00–7,00 | 7–14 | 3,00 guld-ljusläcka flash-through · 3,00/3,25/3,50 ”Med friskvårdsbidraget.” ord för ord · 4,00 guldsfär föds, räknar 0 → 5 000 · **6,00 landar** (sub-boom + chockvåg + shimmer, ”kr/år”) · 6,5 sfären andas |
| 3 | Produkt | 7,00–13,00 | 15–26 | 7,00 riktig sajt tippar upp ur djupet (rotateX) · 8,00 guldmarkör sveper ”friskvårdsbidraget” + push-in · 9,00 kameran tiltar ner till priskorten · 9,50 cursor in · 10,50 klick på ”2,000 kr Populärast” · 11,00 kortet lyfter ut i 3D, sidan blurras · 11,50/12,00/12,50 Greenfee · Range · Lektioner · 12,75 kortet flyger mot kameran |
| 4 | Köpväg | 13,00–16,00 | 27–32 | 13,00 sökfält + rubrik ”Sök Golfkuponger i din portal” · 13,25–14,00 skriver ”Golfkuponger” · 14,00/14,25/14,50/14,75 Benifex · ePassi · Söderberg & Partners · Edenred flyger in som glasbrickor · 15,00 rutnätet tippar i perspektiv · 15,50–16,00 kameran dyker igenom (riser) |
| 5 | Bevis | 16,00–21,00 | 33–42 | **16,00 drop: 300+ slår in** · foton byts 16,00 Bro Hof Slott · 17,00 Halmstad GK · 18,00 Falsterbo GK · 19,00 Österåker GK (whip/zoom, skylt byts i samma ruta) · kick på varje mellanslag · 20,00 flare-chockvåg, ”i hela Sverige” |
| 6 | CTA | 21,00–25,00 | 43–50 | 21,00 whip till djupgrönt · emblemet suddigt, driver · **22,00 skärps** (chime, glöd) · 22,50 ordmärke · 23,00 ”Låt chefen bjuda.” · 23,50 golfkuponger.se + portalrad · **24,00 glanssvep på slutackordet** · 25,00 slut |

Format: master 9:16; 1:1 och 4:5 är samma tidslinje med omkomponerade lägen (`data-fmt` på roten styr CSS + JS-konstanter).
Fakta på skärmen: greenfee/range/lektioner, 300+ klubbar, portalerna, golfkuponger.se, ”upp till 5 000 kr/år” (**F7 overifierat** – noteras i leveransen, ordet ”skattefritt” används inte).
