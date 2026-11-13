# iMessage-samtal (9:16) – arbetsversion

En inzoomad iPhone med ett iMessage-samtal i ljust tema, utan hållare. Allt innehåll ligger i `conversation.json`. Tiderna räknas fram automatiskt. Det finns ännu ingen redigerare i dashboarden.

## Ändra samtalet

1. Redigera `conversation.json`:

| Fält | Betydelse |
| --- | --- |
| `contact` | Namnet i rubriken. Initialerna visas om `avatar` saknas. |
| `avatar` | Profilbild, t.ex. `assets/alex.jpg` (valfri). |
| `clock`, `date` | Klockan i statusraden och stämpeln överst (`9:41`, `Idag`). `stamp: ""` döljer stämpeln. |
| `unread` | Siffran vid bakåtpilen (0 döljer den). |
| `service` | `"sms"` ger gröna bubblor och "Textmeddelande". |
| `largerText` | `false` ger iPhones standardstorlek. Standard är "Större text", som är lättare att läsa i video. |
| `receipt`, `receiptText` | "Levererat" under ditt senaste meddelande (`false` stänger av). |
| `typing`, `showTyping` | Skriver-prickar för den andra / text som skrivs i fältet för dig (`false` stänger av). |
| `typingSpeed` | 1 = normalt, 1,5 = snabbare skrivande. |
| `sentTypingSpeed` | Egen skrivhastighet för dina meddelanden (tangentbordet); 0,5 = hälften så snabbt som normalt. |
| `background` | Bakgrund bakom telefonen: färg (`#e9e7e3`) eller bild i `assets/`. |
| `sounds` | Standard är iPhones egna ljud (`SentMessage`, `ReceivedMessage`). Egna filer: `{"sent": "assets/x.mp3", "received": "assets/y.mp3", "volume": 0.8}`. `false` = tyst. |
| `keyboard` | `true` = iPhones svenska tangentbord syns, med förstorade bokstäver när de trycks och iPhones egna tangentklick. Det glider ner efter ditt sista skrivna meddelande om något kommer efter, t.ex. en bild. Går också att välja med `IMESSAGE_KEYBOARD=1/0 node build.mjs`. |
| `keyboardSounds`, `keyboardVolume` | `false` = tyst tangentbord; volym 0–1 (standard 0,7). |
| `intro` | Låsskärm som intro: `{"lockscreen": true, "date": "fredag 13 november", "wallpaper": "assets/bild.jpg", "sound": "assets/ljud/Rebound.wav"}`. Första meddelandet kommer som notis (standardljud Tri-tone), och appen öppnas när notisen hunnit läsas. |
| `outro` | `"spotlight"` = filmen tonar till mörkgrönt och Golfkupongers slutbild Spotlight (3,1 s, med eget ljud) läggs sist. |
| `endHold` | Sekunder som sista meddelandet står kvar innan filmen slutar (t.ex. 4 för en poäng på slutet). |
| `duration` | Valfri längd i sekunder. Bygget stoppar om den är för kort. |

Varje meddelande i `messages`:

| Fält | Betydelse |
| --- | --- |
| `side` | `"sent"` (du, blå till höger) eller `"recv"` (den andra, grå till vänster). |
| `text` | Texten. 1–3 emoji utan annan text visas stora utan bubbla, som på en iPhone. |
| `image` | Bild i `assets/`. Med `text` visas bilden och textbubblan under. |
| `reaction` | Reaktion, t.ex. `"❤️"`, som dyker upp en stund efter meddelandet. `reactionAfter` = sekunder efter. |
| `sound` | Eget ljud för meddelandet, eller `false` för tyst. |
| `at` | Tvinga en starttid i sekunder. Den får inte bryta läsregeln. |
| `typing` | `false` = meddelandet kommer utan skriv-fas. |
| `overlay` | Bara på bildmeddelanden. En bild som glider rakt ner på bilden, t.ex. pixelglasögon ("deal with it"): `{"src": "assets/glas.png", "x": 0.55, "y": 0.23, "width": 0.64, "rotate": 9, "after": 1, "duration": 1.6, "hold": 2.5}`. Mitten (`x`, `y`) och `width` anges som andel av bilden. `rotate` i grader, `after` = sekunder efter bilden, `hold` = sekunder som filmen fortsätter efter landningen. `IMESSAGE_OVERLAYS=0` stänger av. |

2. Kör `node build.mjs`. Första gången hämtar den Apples resurser till `~/.cache/imessage-mall` (se nedan). Det skriver ut tidslinjen per meddelande och stoppar med en svensk förklaring om något är fel. Det kan till exempel vara en fil som saknas, eller en tid som bryter läsregeln: varje meddelande syns minst max(5/6, tecken/12) + 0,9 s innan nästa kommer.
3. `npm run dev` startar förhandsvisningen, `npm run check` kör den tekniska kontrollen och `npm run render` skapar en MP4.

`node --test build.test.mjs` testar tidslinjen.

## Vad som stämmer med en riktig iPhone

- Tråden börjar uppifrån och scrollar först när skärmen är full.
- Skriver-prickarna och "Levererat" tar egen plats och skjuter upp tråden.
- Svansen sitter bara på sista bubblan i en följd från samma person.
- Rubriken är frostad och bubblorna glider in under den.
- Dina meddelanden skrivs tecken för tecken i fältet, med skicka-knapp, innan de skickas.

## Apples resurser (inte i git)

Jonas beslutade 2026-11-12 att mallen ska använda Apples typsnitt, emoji och meddelandeljud exakt. Repot är publikt, så filerna får inte committas. `.gitignore` håller dem utanför. `apple-resurser.mjs`, som körs av `build.mjs`, hämtar dem till `~/.cache/imessage-mall` (eller `$IMESSAGE_CACHE`) och kopierar dem in i `assets/`.

| Resurs | Källa |
| --- | --- |
| SF Pro Text och Display | Apples officiella paket, [developer.apple.com/fonts](https://developer.apple.com/fonts/). Packas upp med 7-Zip. |
| Apple Color Emoji (macOS 26) | [samuelngs/apple-emoji-ttf](https://github.com/samuelngs/apple-emoji-ttf), fast version. Bara samtalets emoji läggs i `apple-emoji.woff2` (pyftsubset via `uvx`). |
| Sms-signaler Tri-tone och Rebound | iOS-filerna via [rob-paprocki/iOS-System-Sounds](https://github.com/rob-paprocki/iOS-System-Sounds) (fast commit). |
| SentMessage, ReceivedMessage och tangentklick (`key_press_click`, `key_press_modifier`, `key_press_delete`) | iOS-filerna i `/System/Library/Audio/UISounds`, via [extratone/iOSSystemSounds](https://github.com/extratone/iOSSystemSounds) (fast commit), omvandlade till wav. |
| Telefonram `iphone-17.png` | Jonas fil (1311 × 2708 px). Hämtas från cachen eller `Downloads/iphone17-3d-flat.png`. |

Kräver node, ffmpeg, 7-Zip och uv (eller `fonttools[woff]`). Apples licens för SF Pro gäller i första hand gränssnittsmockuper för Apples plattformar. Användningen i reklam är Jonas beslut.

## Begränsningar

- Ingen jämförelse med en riktig skärminspelning är gjord ännu.
- Fler mockuper för vinklade telefoner finns i `docs/research/iphone-mockups-2026-11-12.md`.
