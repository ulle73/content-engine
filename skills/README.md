# Skills

Kunskap som AI:n läser innan den skapar något. Få men djupa.

| Skill | Vad den kan |
|---|---|
| `ad-studio` | Hur idésamtalet leds: förslag före frågor, mall för första svaret, exempel, storyboardregler, kvalitetsgranskning med poäng |
| `golfkuponger-brand` | Bildspråk, färger, typografi, safe zones, rörelse, ton |
| `golfkuponger-friskvard` | Faktabank (med verifieringsstatus), köpvägar, säsong, frågor, vinklar, storyboard-mönster |

Flödet: idésamtal → `engine/ad_studio/brief.py` (`AdBrief`) fylls stegvis → `lock()` → produktion läser bara den låsta briefen.
`AdBrief.missing()` styr vilken fråga som ställs härnäst. `AdBrief.problems()` säger varför den inte går att låsa än.
