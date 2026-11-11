# Ringportal – kameran dyker genom en glödande cirkel  (`teknik.ringportal-kapitelbyte`)

**Roll:** övergång · **Medium:** video

Glödande ringbågar snurrar in runt mitten, sluts till en cirkel och kameran dyker genom den – på andra sidan väntar nästa kapitel.

## Så går den till
1) Tunna, glödande ringbågar (olika radier, olika hastighet) roterar in. 2) De sluts till en ring som ramar in texten eller tomrummet. 3) Ringen skalar upp förbi kameran (eller en liten cirkel i mitten växer) och avslöjar nästa scen/bakgrund. Variant: ringen krymper till en punkt → loggan.

## Varför den fungerar
Samma övergång varje gång blir filmens 'leitmotiv' – tittaren lär sig att ett nytt kapitel börjar. Rörelse mot mitten drar blicken dit nästa text kommer. Känns premium utan bilder.

## Tajming
Bågarna in 0,8–1,2 s, genomdyket 0,4–0,6 s med ease-in. Referensen använder den 5 gånger på 55 s (var ~10:e s).

## Så bygger vi den
- **Tecknat:** HyperFrames/GSAP: SVG-cirklar med stroke-dasharray + rotation + glow (filter drop-shadow); scale 1→8 med clip-path circle() för nästa scen. Färdig nära släkting: hf-skeletons.shader.sdf-iris (cirkulär iris-wipe med glödande ring).
- **Filmat:** Fungerar inte filmat – läggs som grafik över/mellan klipp.

## Idé för Golfkuponger
Ringen = golfhålet: bågarna sluts till koppen, kameran dyker ner i hålet → nästa kapitel. Eller golfbollen sedd uppifrån.

## Bevis
- källa: Lokal fil: Downloads/spotify-new-app-reveal.mp4 (nedladdad av Jonas 2026-11-11)
- kreatör: Spotify (officiell app-reveal/lanseringstrailer)
- likes: None
- kommentarer: None
- datum: None
- lokal_kopia: work/references/spotify-new-app-reveal/
- notering: 55 s, 16:9, inga hårda klipp – bara mjuka övergångar. Länk, siffror och datum saknas (lokal fil). Inspo för app-lanseringar. Vi lånar greppen, aldrig Spotifys färger, bilder, formuleringar, ljud eller logga.

**Tekniken:** godkänd 2026-11-11 (bevisad – skickad/godkänd av Jonas).
**Vårt eget exempel:** ej byggt än – visa ett utkast och låt beställaren godkänna

Används i: –
