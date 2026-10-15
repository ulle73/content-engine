---
name: ljud
description: Regler och arbetsgång för ljud i video och annonser – musik, ljudeffekter, mixning, loudness, synk, licenser och ljudkällor. Använd ALLTID när en video får ljud (musik, SFX, voice-over), när ljud ska väljas, bytas eller mixas, och när någon säger att ljudet låter fel.
---

# Ljud i video – regler och arbetsgång

> Bygger på professionella källor (längst ner) och på det ägaren sagt om våra egna filmer.
> Siffrorna är startpunkter, men lärdomarna under 0 är hårda regler.

## 0. Hårda regler

1. **AI:n kan inte lyssna.** Mät allt (nivåer, synk, takt), men låt en människa välja med öronen.
   Gör en **ljudprovning** innan ljud spikas: varje kandidat i sitt moment, numrerad i bild
   (t.ex. "HELLJUS H1–H6", "SIKTE S1–S6"), så svarar beställaren med ett nummer. Säg alltid att du inte har lyssnat.
2. **Bara riktiga, producerade ljud** – aldrig ljudeffekter syntetiserade i kod (numpy-pip, sinus-ping, brus-whoosh).
   De lät "konstiga" och oproffsiga (FAIV, 2026-10-12). Kod får klippa, flytta, tonhöjdsjustera och mixa riktiga ljud.
3. **Färre ljud.** Ett hjältljud per moment. Välj det minsta antal effekter som berättar scenen.
   Murchs "lag om två och en halv": fler än ~2,5 likartade lager samtidigt blir gröt.
4. **Filmen ska fungera utan ljud.** Budskapet bärs av bild och text; ljudet förstärker. Många ser utan ljud
   (särskilt i Facebook-flödet), men på TikTok och i Reels är ljud på det normala – så ljudet måste också vara bra.
5. **Ändra aldrig ett ljud som beställaren godkänt** när annat justeras: lås dess fil, tajming, panorering och slutliga nivå i koden med en kommentar.

## 1. Planera ljudet från början

Ljud är en del av berättelsen, inte pålägg i slutet (Randy Thom, *Designing a Movie for Sound*).
Gör en **ljudkarta** per beat innan något väljs: vilken känsla, vad ljudet gör (spänning, lättnad, accent), var det ska vara **tyst**.

Exempel (FAIV "Hitta faran"): stressande puls i 120 BPM under nedräkningen → två bildrutors tystnad →
klick + bas + svep när extraljuset tänds → lugnt och harmoniskt → musiken klingar ut när bilden går över till slutkortet → tyst logga.

## 2. Hierarki och nivåer

Ordning, starkast först: **tal → hjältljudet i huvudmomentet → musik → övriga effekter → ambiens.**

- **Musik under tal:** dra ner musiken 6–12 dB när någon pratar (attack 30–80 ms, release 250–700 ms).
  Motorn gör det med `sidechaincompress` i `edit-renderer/src/finish.js`.
- **Effekter är accenter:** ungefär 3–6 dB över musiken (RMS i 50 ms-fönster), inte mer.
  Bas-impacter 9 dB över musiken i två sekunder dränkte allt och lät amatörmässigt (FAIV v3). Korta impacternas svans (≤ 1,3 s).
- **Huvudmomentet ska vara starkast** (i FAIV-filmen: när ljuset tänds), detaljljud (siktet, tick) tydligt svagare.
- **Kontrast före kraft:** ett ögonblicks tystnad (2 bildrutor) före ett stort moment gör mer än en högre smäll.
- Mät nivån per moment efter mixen och skriv ut den (se 9), så att hierarkin går att kontrollera utan öron.

## 3. Loudness och toppar vid leverans

| Mål | Integrerat | True peak |
|---|---|---|
| **Sociala medier/webb (vår standard)** | **-14 LUFS** | **≤ -1 dBTP** (motorn: -1,5) |
| Spotify / YouTube | -14 LUFS (YouTube sänker bara, höjer aldrig) | -1 dBTP |
| TikTok / Instagram | Ingen publicerad spec – använd -14 och provladda | -1 dBTP |
| Apple Music | -16 LUFS | -1 dBTP |
| AES TD1008 (strömmat ljud) | tal -18, musik -16 LUFS | – |
| Broadcast EBU R128 | -23 LUFS | -1 dBTP |
| Netflix | -27 LKFS (dialoggrindat) | -2 dBTP |

- Normalisera med **två-pass `loudnorm` och `linear=true`**: hela mixen höjs lika mycket, så balansen bevaras (se 9).
- **Normalisera inte ett glest spår** (några enstaka effekter utan musik eller tal) till -14 – det drar upp effekterna orimligt.
  Leverera det på sin nivå och normalisera först när musik eller tal bär ljudet.
- Motorns QA (`edit-renderer/src/qa.js`) varnar när nivån avviker mer än 1 LU från målet och när toppen går över -0,5 dBTP.

## 4. Synk

- **Ljud får inte komma före bilden.** Tittare märker ljud som ligger ~45 ms före eller ~125 ms efter bilden
  (ITU-R BT.1359, mätt på tal). Sikta på exakt bildruta; hellre en bildruta sent än tidigt.
- **Placera på ljudets uppmätta ansats eller topp, inte på filens början.** Många filer har 50–300 ms luft eller
  en uppbyggnad före smällen: mät ansatsen och toppen och dra av den (`place(..., t - onset)`).
- Ljud som följer en rörelse (whoosh på en slider) läggs strax efter rörelsens start (~0,15–0,2 s), där rörelsen syns.
- Räkneverk, timer, tick: koppla ljudet till samma kurva som bilden (samma easing), inte till en fast takt.
  Lägg en minsta lucka (~28 ms) så att klicken inte smälter ihop till ett surr, och ett tydligare "lås" när siffran stannar.
- Kontrollera i riktig uppspelning, inte bara på tidslinjen.

## 5. Musik

- **Välj musiken först**; lägg sedan effekterna på dess slag.
- **Följ dramaturgin:** byt karaktär på vändpunkten (stress → lugn när problemet löses). Två spår med en tydlig övergång
  fungerar ofta bättre än ett spår som ska passa allt.
- **Tempo efter de rytmiska elementen** i filmen: tic-tac var 0,5 s = 120 BPM. Mät spårets takt och fas och lägg
  slagen exakt på tick-ljuden.
- **Klipp på slag och fraser**, aldrig mitt i ett slag: lägg klippet i dalen precis före nästa slag.
- **Backtiming:** placera låtens naturliga slut där musiken ska sluta – vid sista bildrutan, eller tidigare om
  slutkortet ska vara tyst. Låt den klinga ut; tona inte bort mitt i en fras.
- **Leverera stems:** musik och effekter som separata filer, så att musiken kan bytas utan att effekterna rörs.
- Premium och mörkt tilltal: minimal filmisk elektronika, piano och stråkar. Undvik glad reklampop och "episk trailer med kör".

## 6. Ljudeffekter

- **Bygg i lager efter jobb:** transient (klick, 4–12 kHz) + kropp (80–500 Hz) + eventuellt sub (20–80 Hz) och svans eller rymd.
  Alla behövs inte. Kropp utan transient låter dovt; transient utan kropp låter som en leksak.
  Exempel, FAIV "ljuset tänds": skarp brytare (transient) + brytare med basstöt (kropp), samtidigt + filmiskt svep vars topp landar 0,3 s senare när ljuset fyller skogen.
- **Mobilen:** telefonhögtalare återger nästan ingen sub. Ett ljud som bara lever under ~100 Hz försvinner där.
  Se till att varje viktigt ljud har energi i mellanregistret; låt basen höras via övertoner (100–250 Hz). Kolla i mono.
- **Inga spel- eller tecknade ljud i premiumfilm** ("gaming lock", "magic sparkle", glada chimes, pip).
- Lätt panorering (±0,1–0,5) ger rörelse; håll basen i mono.
- Ett tic-tac: samma klick, tic några halvtoner upp och tac några halvtoner ner (t.ex. +2 och -6), så att de tydligt skiljer sig.

## 7. Källor och licenser (reklam)

| Källa | Reklam? | Notering |
|---|---|---|
| **Pixabay** (finns lokalt: `~/.claude/skills/media-use/audio/assets/sfx`, ~20 ljud) | Ja, ingen attribution | Får inte säljas eller spridas som lösa ljud |
| **Mixkit** (`assets.mixkit.co/active_storage/sfx/<id>/<id>-preview.mp3`) | Ja – licensen nämner reklam online och sociala medier | **Får inte ligga i mallar eller verktyg** → bara i `work/`, aldrig i `library/` |
| **Sonniss GDC-paketen** (gratis varje år, flera GB) | Ja, royaltyfritt, ingen attribution | Inte för AI-träning; inte vidareförsäljning |
| **Freesound** | Bara **CC0** och CC BY (kräver namn på upphovspersonen) | **Aldrig CC BY-NC** |
| **TikTok Commercial Music Library / Meta Sound Collection** | Ja, inom respektive plattform | Företagskonton får inte använda vanliga topplåtar i annonser |
| **Epidemic Sound / Artlist** | Ja, med företagslicens | Bäst utbud; stems och förlängda versioner |
| **ACE-Step** (lokal musikgenerering, `library/tools/make_music.py`) | Eget material | Generera 2 tagningar, välj med mätning (puls, dynamik, naturligt slut) och lyssning |
| BBC Sound Effects | **Nej** (icke-kommersiellt) | Använd inte |

Spara alltid källa, licens och id i en `SOURCES.txt` bredvid ljudfilerna. Läs licensen på källans egen sida innan första användningen.

### Ljudbanken – börja här, spara hit (Jonas 2026-10-13)

`library/sounds/` är banken med **godkända** ljud: roll ("när passar det"), sökord, källa, licens, exakt godkänt
utdrag (`cut`) och nivåtips per ljud. Sök först där: `python library/tools/find.py "<moment>" --type sound` eller
`python library/sounds/sounds.py list`, och hämta med `python library/sounds/sounds.py copy <id> work/<film>/sfx/<namn>.wav [--cut]`.

**Varje ljud beställaren godkänner sparas i banken i samma session** – även musik och ljud hen själv skickat:
lägg till en rad i `library/sounds/make_library.py` (id `sound.<vad-det-är>`, roll, sökord, källa, licens, fil eller url+md5,
utdrag, nivåtips, vilken film) och kör den (skriver `LIBRARY.json` + vågformsbild), sedan `build_catalog.py`.
CC0, Pixabay och eget material läggs i `library/sounds/files/`. **Mixkit läggs aldrig i git** – bara url + md5; `sounds.py`
hämtar till `library/sounds/.cache/` (gitignorerat). Ljud som underkändes sparas inte (nämn dem i filmens `SOURCES.txt`).

## 8. Arbetsgång

1. **Ljudkarta** per beat (känsla, vad ljudet gör, tystnad).
2. **Musik:** välj eller generera, mät takt och fas, bestäm var den börjar, byter karaktär och slutar.
3. **Kandidater** per moment (3–6 st) ur källorna ovan; mät ansats, topp, längd, tonläge och energikurva.
4. **Ljudprovning:** en video med varje kandidat i sitt moment, numrerad i bild. Beställaren väljer.
5. **Mixa:** hjältljudet starkast, effekter 3–6 dB över musiken, tystnad före stora moment. Mät nivån per moment.
6. **Loudness:** två-pass loudnorm till -14 LUFS, topp ≤ -1 dBTP.
7. **Kontroll:** telefonhögtalare, mono, låg volym, och utan ljud (bär bilden budskapet?).
8. **Leverera:** video + stems (musik, effekter) + `SOURCES.txt`.

## 9. Mätkommandon

```bash
# Integrerad loudness, LRA och topp för en färdig fil
ffmpeg -hide_banner -nostats -i film.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -E " I:|LRA:|Peak:"

# Två-pass loudnorm: mät först …
ffmpeg -hide_banner -nostats -i mix.wav -af loudnorm=I=-14:TP=-1.0:LRA=20:print_format=json -f null -
# … och använd sedan värdena (input_i, input_tp, input_lra, input_thresh, target_offset) med linear=true
ffmpeg -i video.mp4 -i mix.wav -filter:a "loudnorm=I=-14:TP=-1.0:LRA=20:measured_I=…:measured_TP=…:measured_LRA=…:measured_thresh=…:offset=…:linear=true" -c:v copy -c:a aac -b:a 256k ut.mp4
```

Nivå per moment (Python): RMS i 50 ms-fönster runt varje händelse; jämför hjältljud, effekter och musik.
Ansats: första punkten där energin (kvadrat, glidande 5 ms) passerar ~2–5 % av max. Takt: spektralt flöde, testa faser för känd period.
Takt och fas i en låt: `node .claude/skills/animate/tools/beats.mjs <låt.wav> <utkatalog>` (tempo, slag, takter, starkaste träffar, tysta partier).
Motorns egen mixning och QA: `edit-renderer/src/finish.js` och `edit-renderer/src/qa.js`.

## Källor

- Loudness per plattform: [Fora Soft – LUFS targets per platform 2026](https://www.forasoft.com/learn/audio-for-video/articles-audio/lufs-targets-per-platform-2026),
  [OpenClip – LUFS targets](https://openclip.app/learn/audio-normalization), [AES TD1008 (Production Advice)](https://productionadvice.co.uk/td1008/),
  [Telos – loudness för strömmat ljud](https://docs.telosalliance.com/docs/understanding-loudness-for-streaming-audio)
- Netflix: [Sound Mix Specifications & Best Practices](https://backlothelp.netflix.com/hc/en-us/articles/360001794307-Netflix-Sound-Mix-Specifications-Best-Practices-v1-5)
- Synk: [ITU-R BT.1359 toleransfönster (Fora Soft)](https://www.forasoft.com/learn/audio-for-video/articles-audio/lip-sync-itu-r-bt-1359-tolerance-windows),
  [TV Technology – A/V sync, how bad is bad](https://www.tvtechnology.com/opinions/av-synchronization-how-bad-is-bad)
- Musik till bild: [PremiumBeat – snyggt slut på musiken](https://www.premiumbeat.com/blog/cap-your-music-tracks-for-a-smooth-ending/),
  [Storyblocks – klippa på slaget](https://www.storyblocks.com/resources/wp-json/wp/v2/tutorial/25313),
  [Musikklipp som känns avsiktliga](https://davinciresolve21.com/blog/how-to-make-a-music-edit-sound-intentional)
- Ducking: [Corel – audio ducking](https://learn.corel.com/tutorials/pinnacle-use-audio-ducking/),
  [DaVinci Resolve – ducka musik under dialog](https://tryuncle.com/learn/davinci-resolve/how-to-duck-background-music-under-dialogue-in-davinci-resolve)
- Mobilhögtalare: [Varför mixen låter annorlunda i telefonen](https://sounddesign.irpr.agency/guides/why-does-my-mix-sound-different-on-phone/),
  [Varför basen försvinner](https://loststoriesacademy.com/blogs-and-tutorials/why-your-bass-disappears-on-speakers)
- Lager och "less is more": [IRPR – layering](https://sounddesign.irpr.agency/glossary/layering/),
  [Krotos – sound design i film](https://krotos.studio/blog/what-is-sound-design-in-film)
- Filmljudets principer: [Randy Thom – Designing a Movie for Sound](https://filmsound.org/articles/designing_for_sound.htm),
  [Walter Murch om lagen om två och en halv](https://sound.krotosaudio.com/?p=1418)
- Plattformar: [TikTok – Commercial Music Library](https://ads.tiktok.com/business/zh/blog/audio-library-royalty-free-music),
  [Social Media Today – TikToks musikregler för företag](https://www.socialmediatoday.com/news/tiktok-changes-rules-on-music-usage-by-businesses/577734/),
  [Meta – video utan ljud (sammanställning)](https://www.jumpfly.com/blog/video-best-practices-for-meta-ads-maximizing-your-campaigns-impact/)
- Licenser: [Mixkit License](https://mixkit.co/license/), [Pixabay FAQ](https://pixabay.com/service/faq/),
  [Sonniss GDC 2026](https://rekkerd.org/sonniss-releases-gdc-2026-game-audio-bundle/), [Freesound (licenser)](https://en.wikipedia.org/wiki/Freesound)
