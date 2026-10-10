# Återanvändning och licensgränser

Den aktiva applikationen innehåller inte Brightbean. Dess submodul, Python-importer, modeller, sidmall, beroendelista och byggkedja har tagits bort. Den nya sidramen, konfigurationen och företagsmodellen är självständigt skrivna för detta projekt. Ingen Postiz-serverkod kopieras eller körs här.

- **Social Media Skills:** https://github.com/social-media-skills/skills, MIT, låst submodulrevision 6e30eeb2f6736bda8683b6bbaa674af3641d7945. Ursprungliga skilltexter och MIT-notice finns kvar i `vendor/social-media-skills/`. Fyra befintliga skills läses vid generering, utan att deras instruktioner skrivs om till en egen innehållsmotor.
- **Django:** https://github.com/django/django/blob/main/LICENSE, BSD-3-Clause. Färdig autentisering, lösenordshashning, formulär, sessioner, CSRF och ORM används som bibliotek.
- **Hosted Postiz:** https://docs.postiz.com/public-api/introduction. Extern tjänst via HTTP API. Konton, abonnemang och tjänstevillkor hanteras hos Postiz.
- Övriga Python-bibliotek installeras från `requirements.txt` och behåller sina medföljande licenser. Exempel: OpenAI SDK och HTTPX (Apache-2.0/BSD respektive BSD), cryptography (Apache-2.0 eller BSD), psycopg (LGPL-3.0). Att ta bort Brightbean betyder inte att tredjepartslicenser upphör att gälla.

Ingen ny öppen licens tilldelas projektets egen kod utan ägarens val. Tidigare revisioner med Brightbean och AGPL finns kvar i Git-historiken, med sina dåvarande licensvillkor. De har inte retroaktivt omlicensierats. Licenstexten för den tidigare versionen finns under `docs/licenses/`.

- **Inter** (typsnitt för storyboard- och granskningsbilder): https://github.com/rsms/inter, SIL Open Font License 1.1. Licenstext i `engine/ad_studio/fonts/Inter-OFL.txt`.
- **Typsnitt i molnklippningen** (`edit-renderer/fonts/`, inbäddade i varje klipp, hämtas aldrig från nätet vid rendering): Inter (https://github.com/rsms/inter), Anton (https://github.com/googlefonts/AntonFont), Caveat Brush (https://github.com/impallari/CaveatBrush) och Playfair Display (https://github.com/clauseggers/Playfair-Display) – alla SIL Open Font License 1.1, oförändrade. Upphovsrätt och licenstext i `edit-renderer/fonts/OFL.txt`.
- **Ljudeffekter i molnklippningen** (`edit-renderer/src/sfx.js`): syntetiseras i kod vid rendering (egen JS-port av projektets `library/prompts/motion-studio-playbook/sfx_synth.py`); inga inspelade tredjepartsljud.
