# Remotion-bibliotek: urval och kvalitetsplan

Undersökt 2026-10-03. Detta är ett researchunderlag och ett eget svenskt
promptpaket. Inga externa skills, komponenter eller mediefiler har installerats,
och inget har importerats till företagens bibliotek eller publicerats.

## Rekommendation

Bygg ett litet bibliotek av valbara, visuellt testade mallar med tydliga
materialkrav. Varje mall kombinerar ett promptrecept, en bestämd scenstruktur,
registrerade renderkomponenter och kvalitetsregler. AI:n fyller innehållet och
föreslår lämplig mall utifrån brief, material och budget.

Ett promptrecept påverkar planeringen. En renderkomponent bestämmer utseendet.
En coding skill hjälper utvecklaren att bygga komponenten. Att installera en
skill i Codex gör den inte automatiskt tillgänglig för webbappens AI-planerare.

## Källor värda att använda

| Källa | Nytta för Content Engine | Anpassning och verifiering |
| --- | --- | --- |
| [Remotion Elements](https://www.remotion.dev/elements) | Små visuella byggblock med källkod och förhandsvisningar. | Förstahandsval för nya registrerade komponenter. Kontrollera beroenden och respektive användningsvillkor vid import. |
| [Rotating Cards](https://www.remotion.dev/elements/commerce/product-collection/) | Bra förebild för användarens bildkarusell: originalbilder får ta plats i tur och ordning. | Exemplet har tre kort och är kvadratiskt. Anpassa antal bilder, 9:16/16:9, bildpassning och text. Källan använder Interactive och andra API:er vars kompatibilitet med vår låsta Remotion 4.0.530 ännu inte är verifierad. |
| [Social Safe Zones](https://www.remotion.dev/elements/overlays/social-safe-zones/) | Visar var Instagram/TikTok-gränssnitt riskerar att täcka innehåll. | Lägg som valbar guide och kontroll i förhandsvisningen. Exemplen gäller 1080x1920 och representativa appvyer; zonerna är inte en garanti för alla enheter eller appversioner. |
| [Number Counter](https://www.remotion.dev/elements/data/number-counter/) | Animerad statistik för sammanfattningar och resultat. | Vi har redan räknare; jämför behandling och läsbarhet innan vi lägger till en variant. Använd verifierade värden. |
| [Officiella Remotion Skills](https://github.com/remotion-dev/skills) | Riktlinjer för animation, typografi, media, ljud, captions och rendering. | Motsvarande skills finns redan tillgängliga i utvecklingsmiljön. Använd dem för implementation och granskning; översätt utvalda råd till appens mallregler. |
| [Prompt Showcase](https://www.remotion.dev/prompts) | Exempel på prompt och resultat för att jämföra kreativa upplägg. | Inspirationskälla för egna recept. Galleriet är inte ett löfte om licens eller färdig integration för varje exempel. |
| [TikTok-template](https://www.remotion.dev/templates/tiktok) | Lokal Whisper.cpp-transkribering och animerade undertexter ord för ord. | Bra senare tillägg för klipp med tal. Kräver en separat transkriberingspipeline och svensk QA. Lokal körning använder beräkningsresurser. |
| [Marketing Video Skill](https://github.com/xsourabhsharma/remotion-marketing-video-skill) | Referenser för marknadsfilmsstruktur, demo, ljudmix och granskningsflöde. | Community-kandidat. [MIT-licens verifierad](https://github.com/xsourabhsharma/remotion-marketing-video-skill/blob/master/LICENSE); komponenternas visuella kvalitet har inte testats här. Börja med narrativa regler. |
| [HyperFrames](https://github.com/heygen-com/hyperframes) | Kreativa skills och register med exempel på övergångar, overlays och datavisualisering. | Apache-2.0 enligt projektets licens. Tekniken bygger på HTML och skiljer sig från vår React-renderare. Välj designidéer och porta dem till registrerade Remotion-komponenter. |

[Remotions mallkatalog](https://www.remotion.dev/templates) innehåller både
kostnadsfria projektmallar och betalda produkter. Många är startprojekt för en
app snarare än färdiga annonsutseenden. Exempelvis
[Prompt to Motion Graphics](https://www.remotion.dev/templates/prompt-to-motion-graphics)
är en arkitekturreferens för AI-genererad kod och browser-preview. Det kräver ett
annat körningsupplägg än vårt stängda MotionSpec och är inte en direkt import.

Remotions [Element Guidelines](https://www.remotion.dev/elements/guidelines)
stödjer fokuserade, återanvändbara byggblock med få beroenden och representativa
videoförhandsvisningar. Det passar vår katalog bra.

Ett ytterligare sökträffsbibliotek, video-shotcraft, gick inte att öppna direkt
på GitHub vid kontrollen. Det tas därför inte med bland rekommenderade importer.

## Vad som begränsar vår app idag

Verifierat mot main 560e589, 2026-10-03:

- `engine/motion/catalog.json` innehåller 17 mallar och 85 andra poster för
  komponenter, bakgrunder, effekter och övergångar. Katalogstatus är inte ensam
  bevisning för visuell kvalitet.
- `engine/assistant/workflows.py`, `motion_compile()`, väljer `kinetic-text`
  för nya vanliga Motion-projekt. Val av promptrecept väljer inte en annan
  renderingsmall. Befintliga video- och redigeringsvägar har separata grenar.
- `engine/motion/planner.py`, `compile_template()`, återanvänder normalt samma
  textprops i flera scener. `monthly-wrapped` har specialbehandling. Scenerna
  behöver egna budskap för att ge en riktig berättelse.
- Den vanliga chattskapningen har högst två bildplatser. En karusell med fyra
  bilder behöver stöd för en ordnad materiallista, inte bara ett nytt promptnamn.
- `animated-scroll` är idag en AI-sekvens som skapar klipp mellan bilder.
  En Remotion-bildkarusell animerar originalbilderna och bör vara ett eget tydligt
  val, exempelvis "Bildkarusell – bevara originalbilder".
- Textmätning, generella säkerhetsmarginaler, lästid, ljud- och videokontroller
  finns redan. Förbättra dessa; skapa inte parallella system som gör samma sak.

## Föreslagen implementation i ordning

1. **Koppla in befintliga mallar.** Låt ett validerat mall-ID och versionsnummer
   följa planen till kompilering. Definiera mallens fält, materialroller och
   scenstruktur. Tillåt bara kända mallar och komponenter i MotionSpec.
2. **Ge varje scen eget innehåll.** Exempel: fånga intresse, visa nyttan, visa ett
   belägg, avsluta med nästa steg. AI:n får inte hitta på priser, siffror,
   villkor eller kundcitat. Fråga om avgörande underlag saknas.
3. **Bygg bildkarusellen.** Ordnad lista med 2–8 bilder, tydlig contain/crop,
   beskärningsförhandsvisning, egen text per bild och avslutande logga/CTA.
   Upplösningsvarningar ska utgå från bildens faktiska visningsstorlek.
4. **Gör biblioteket lätt att välja från.** Kort videodemo, format, normal längd,
   antal filer och ett exempel på användning. Filtrera efter bifogat material.
   Låt användaren välja lugnt, balanserat eller energiskt tempo inom testade gränser.
5. **Kvalitetskontroll före visning.** Mät textytor, kontrast, minsta läsbara
   textstorlek, textens hålltid, upprepade budskap och plattformens zoner. Ladda
   typsnitt innan text mäts. För lång text ska kortas eller delas, inte bara
   krympas till minsta tekniskt möjliga storlek.
6. **Kontrollera riktiga renderade bildrutor.** Granska både entré, stabilt läge
   och utgång. En valfri bildanalys kan komplettera mätbara kontroller. Högst två
   automatiska reparationsförsök för text, layout och timing; kvarstående problem
   visas tydligt. Renderad preview ska fortfarande godkännas före slutrendering.
7. **Återanvänd godkända utseenden.** "Spara som företagsmall" fryser layout,
   typografi, färger, logga och rytm i en version. Nästa film byter innehåll i
   definierade platser. Tidigare godkända filmer blir referenser för samma företag.
8. **Lägg till captions för tal.** Transkribering och undertexter blir ett eget
   val med språk och läsbarhetskontroll, efter att kärnflödet fungerar.

Mallprofilen bör innehålla identitet/version, renderer-ID, scenfält,
materialkrav, format, tidsram, textgränser, preview, kvalitetsregler samt käll-
och licensuppgifter. Hämta bara relevanta instruktioner för den valda mallen.
Bevara företagsisolering, immutabla versioner och godkännandekoppling till exakt
förhandsvisning.

## Promptpaket

`remotion-prompt-recipes.sv.json` innehåller åtta egna svenska recept: karusell,
presentkort, banpresentation, stegförklaring, kundcitat, månadssammanfattning,
appdemo och logga/avslutning. Texterna är självständigt skrivna för vår app.

Varje `template_request` följer dagens API-kontrakt och kan sparas som ett
promptrecept. `proposed_renderer_profile` är planeringsmetadata för en kommande
koppling, inte ett implementerat API-kontrakt. Import av bara prompttexten
aktiverar inte de föreslagna utseendena. De befintliga renderingsmallarna behöver
kopplas in och kvalitetsgranskas; karusellkomponenten behöver byggas.

Formatvalidering av promptpaketet är inte ett test av verkliga AI-svar eller
renderade filmer. Externa komponenter har endast granskats som källor.

Kostnadsvisningen bör fortsatt skilja på AI-planering/analys, eventuell betald
bild-/videogeneration och renderingsresurser. Ett promptpaket startar inga sådana
jobb i sig. Ingen ny driftstjänst behövs för själva biblioteket.
