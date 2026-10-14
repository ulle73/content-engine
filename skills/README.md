# Skills

Kunskap som AI:n läser innan den skapar något. Få men djupa.

| Skill | Vad den kan |
|---|---|
| `studio` | **Ingången för allt innehåll.** Söker i Content Library (`library/`) efter färdiga, snygga mallar, effekter, karuseller, skills och prompts, föreslår kombinationer och anpassar |
| `ad-studio` | Hur idésamtalet leds: förslag före frågor, mall för första svaret, exempel, storyboardregler, kvalitetsgranskning med poäng |
| `golfkuponger-brand` | Bildspråk, färger, typografi, safe zones, rörelse, ton |
| `golfkuponger-friskvard` | Faktabank (med verifieringsstatus), köpvägar, säsong, frågor, vinklar, storyboard-mönster |
| `video-regler` | Rätt första gången: beslutsrunda före bygget, husregler för text/bild/slutkort/ljud, QA, lärdomslogg |
| `teknik` | Teknikbanken: bevisade tekniker (krok, retention, vändning, bevis, cta, struktur) – välj inför varje video/karusell; lägg till nya från länkar med `hamta.py` |
| `ljud` | Regler och arbetsgång för ljud i video: musik, ljudeffekter, mixning, loudness, synk, licenser och källor |

Flödet: idésamtal → `engine/ad_studio/brief.py` (`AdBrief`) fylls stegvis → `lock()` → produktion läser bara den låsta briefen.
`AdBrief.missing()` styr vilken fråga som ställs härnäst. `AdBrief.problems()` säger varför den inte går att låsa än.

Claude Code-skills från biblioteket (NextPhase, persa, live-carousel, karusellkit, motion-studio, animate m.fl.) ligger i `.claude/skills/`. Allt indexeras i `library/catalog.json` och syns i `library/gallery.html`.
