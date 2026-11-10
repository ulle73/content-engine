# Golfrealism för AI-bilder – Golfkuponger

**Datum:** 2026-10-28  
**Underlag:** Jonas uppladdade researchrapport *Hyperrealistiska AI-bilder för golf: evidens, promptteknik och praktiska A/B-tester* (24 oktober 2026), nuvarande Content Engine-arkitektur samt [OpenAI Image prompting](https://developers.openai.com/api/docs/guides/image-prompting) och [Image generation](https://developers.openai.com/api/docs/guides/image-generation).

## Evidens och avgränsning

Rapporten bygger på dokumentation och forskning om spatiala/kompositionella fel, **inte på körda Golfkuponger-A/B-tester**. Receptens kvalitetsfördelar är därför **HEURISTIC** tills egna bilder jämförts. Dokumenterade API-funktioner (referenser, redigering) ska inte blandas ihop med uppmätta förbättringar.

Guiden gäller **fotografiska golfbilder**. Den får aldrig förvandla en uttryckligen beställd teckning, 3D-illustration eller annan stil till ett fotografi. Om användaren uttryckligen väljer ett golfrecept är foto däremot själva mallvalet. Golfkupongers befintliga brandregler och officiella loggafiler gäller fortsatt. AI ska inte återskapa riktiga produktloggor, webb-UI eller obekräftade banlandmärken.

## Fem bildrecept i befintliga Creative Recipes

| Recept | När det används | Viktigaste kontroller |
|---|---|---|
| `golf_photo_golfer` – Golfare, naturligt foto | Golfer vid tee, address, vardagligt spel | Händer på ett grepp, obrutet skaft, båda fötter, naturlig hud |
| `golf_photo_swing` – Golfsving, action | Slagrörelse i en uttrycklig fas | Address/backswing/efter träff/follow-through; kroppens vikt, klubban och bollen stämmer med fasen |
| `golf_photo_course` – Svensk golfbana | Landskap, green, fairway, miljö | Fairway/semiruff/ruff/green har olika struktur; mjuka övergångar, normal nordisk vegetation |
| `golf_photo_equipment` – Golfutrustning | Närbild på klubba, bag, putter eller vagn | Tydliga fästen; grepp → ett skaft → hosel → ett huvud; två bagben; 1+2 hjul på trehjulig vagn |
| `golf_photo_campaign` – Naturligt kampanjfoto | Organiskt/annons med plats för copy | Candid pose, skandinaviskt dagsljus, rimlig interaktion, valfri negativ yta för budskap |

Recepten är **inte en ny promptdatabas**: de ligger i det befintliga versionshanterade `engine/creative_recipes.py`, erbjuds som mallar under **Skapa bild** endast för Golfkuponger och sammanställs av den vanliga bildpromptkompilatorn. Ett bildrecept ändrar aldrig videomodellens regler. `generic_image` förblir standard för andra stilar och företag.

## Synliga detaljer i stället för kvalitetsfloskler

- **Händer och klubba:** Beskriv var händerna griper **samma** handtag, att handlederna fortsätter naturligt från underarmarna och att ett obrutet skaft möter hoseln på klubbhuvudets heel-sida. Driver, järn och putter har skilda former.
- **Rörelse:** En uttrycklig svingfas, normal fotkontakt och rätt bollposition. För produktfokus är en statisk address ofta lättare att kvalitetssäkra än en snabb sving.
- **Gräs:** Green är finare/kortare än foregreen; fairway är grövre och mer varierad; ruff är längre. Färgskillnader är subtila, inte neon. Enskilda strån syns i relevant förgrund, inte identiskt på 100 meters avstånd.
- **Foto:** Ange synlig vinkel, avstånd, skärpeplan, naturlig ljusriktning, material och färgbalans. Objektiv/brännvidd är en visuell signal, **inte** en fysisk garant.
- **Komposition:** En tydlig huvudperson och en huvudhandling. Lägg inte till klubbor, andra golfare och rekvisita om de inte behövs.
- **Stil:** Vardagligt redaktionellt/fotografiskt ljus före ord som ”8K masterpiece, epic, award-winning”. Långa generella negativa promptar ersätter inte verkliga relationer.

## Referenser, redigering och stoppregler

1. **Exakt produkt, verklig person, verklig klubb eller specifik svingpose:** begär eller använd befintligt **riktigt referensfoto**. En textprompt kan inte garantera faktisk utrustningsmodell eller plats.
2. Välj några kandidater med fungerande **struktur först**, inte bara snyggast färg. Dyr upplösning är sista steget.
3. Om ett begränsat område är fel: **ändra bara det området** med riktig referens och bevara resten; använd maskredigering endast när adaptern/UI verkligen stöder mask. Nuvarande Content Engine-adapter stöder **en källbild och ingen maskning**. Påstå inte att precis inpainting är implementerad.
4. Vid upprepade geometrier som är fysiskt fel: byt metod/referens/komposit i stället för att lägga till fler adjektiv.

Bildpreflight ger endast **råd**, aldrig falsk garanti om verklig produkt. Varken automatisk visuell granskning eller bevisad bättre golfgeometri är implementerad här.

## Manuell kvalitetspoäng och hårda fel

Bedöm vardera **1–5**: (1) fotografisk trovärdighet, (2) mänsklig anatomi, (3) utrustningsgeometri, (4) gräs och mark, (5) promptföljsamhet, (6) fysisk integration (skuggor, markkontakt, perspektiv). Spara poängen vid senare tester.

**Hard fail** oavsett medelpoäng: huvudklubban är mekaniskt omöjlig, huvudpersonen har uppenbart fel händer/anatomi, eller en central faktisk produkt stämmer inte med originalreferensen. Granska i full storlek.

## Första A/B-testet (inte genomfört)

**Föreslaget pilotupplägg:** fyra golfmotiv × två promptvarianter (enkel A jämfört med strukturerat B) × tre genereringar = **24 bilder**. Håll modellversion, format, referenser, kvalitetsinställning och seed lika där seed stöds. Blanda bilderna före granskning. Dokumentera de sex delpoängen, hard fails, antal godkända bilder, kostnad per godkänd bild och antalet redigeringsförsök. Kör separat C för `B + referens/lokal edit` så att olika metoder inte blandas.

## Förändringsprincip

Gör inga påståenden om förbättrad konvertering eller bildkvalitet förrän ett verkligt test visar utfallet. Företagsspecifika referenser stannar inom företagets befintliga MediaAsset/ContentRun-gränser. Alla betalda genereringar kräver Content Engines befintliga godkännande och kostnadskontroll.
