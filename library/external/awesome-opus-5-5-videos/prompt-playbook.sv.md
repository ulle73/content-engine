# Sju återanvändbara produktionsprompts (svensk bearbetning)

> **Källa och licens:** bearbetad och översatt till svenska från `docs/prompt-playbook.zh-CN.md` i
> [athemeroy/awesome-opus-5-5-videos](https://github.com/athemeroy/awesome-opus-5-5-videos)
> (commit 0b96ca1), © upphovspersonerna, licens **CC BY 4.0**
> (https://creativecommons.org/licenses/by/4.0/). Ändringar: översatt, förkortat, Golfkuponger-tips
> tillagda. Mallarna är repots egna – inte kopierade X-prompts. Hakparenteser byts mot eget innehåll.

## 1. Kodanimation utan externa bilder

```text
Gör en [45] s film i [9:16] med JavaScript + Canvas 2D om [ämne] för [publik].
Inga externa bilder, videor, typsnitt eller bildmodeller; ljud bara från [egen Web Audio-syntes / mina licensierade filer].
Ge först en storyboard med 6–8 tagningar: start/slut, motiv, handling, text och övergång. Bestäm en
figur och en begränsad palett och håll dem genom hela filmen. Rita deterministiska bildrutor och
leverera en källfil som kan renderas om + MP4. Rendera först 5 s provfilm och kontrollera
textöverflöd, figurkontinuitet och rörelsetempo; rätta och rendera sedan allt. Lista till sist
använda filer, ljud och vad en människa behöver granska.
```

## 2. Utbildande explainer – innehållet före bilden

```text
Utifrån [kursplan/källor], gör en [3–5] min introduktion till [ämne] för [publik], så att tittaren
kan förklara [tre lärandemål]. Lista först faktapåståenden, källor och osäkra punkter som jag ska
bekräfta. Skriv sedan manus per tagning och bildplan. Bild i [Manim/Remotion], röst med [TTS],
undertexter från samma tidslinje. Leverera MP4, källkod, manus, källista och undertextfil. Kontrollera
att inget skymmer formler, att undertexter följer tidslinjen och att ljudet inte klipper. Kan du inte
lyssna på resultatet: skriv "rösten är inte avlyssnad av modellen". Inga okontrollerade fakta.
```

## 3. Reklamfilm av en befintlig produkt

```text
Utifrån produktrepot [mapp] och mina [skärmdumpar/varumärkesregler], gör en [20] s reklamfilm i
[16:9/9:16] för [målgrupp]. Använd bara ikoner, typsnitt, skärmdumpar och text som vi har rätt till;
hitta inte på funktioner, användardata eller omdömen. Läs koden och produktbeskrivningen, lista tre
funktioner som faktiskt kan visas, skriv 5 tagningar med ett budskap och riktigt UI-bevis var.
Rendera i Remotion och behåll ett redigerbart projekt. Skicka först en lågupplöst förhandsvisning
för faktagranskning; leverera sedan MP4 och lista återanvända tillgångar, ny grafik, tredjepartsljud
och påståenden som produkt/juridik ska godkänna.
```
*Golfkuponger:* faktabanken i `golfkuponger-friskvard` är "produktbeskrivningen"; riktiga
skärminspelningar av portal/app/kvitto.

## 4. 3D – skilj "bygga scenen" från "filma den"

```text
Gör en [15] s 3D-tagning av [ämne] i [Blender/Three.js]. Lista först objekt, material, ljus,
kamerabana och händelser per sekund; märk vad du genererar och vad som kommer från mina filer.
Ladda inte ner modeller utan licens. Visa först gråmodell och kameraförhandsvisning, sedan slutligt
material och ljus. Leverera MP4, projektfil och tillgångslista med bildfrekvens, upplösning,
renderingstid och kända fel (genomträngning, flimmer). Är det en inspelning av en interaktiv scen: märk den så.
```

## 5. Claude regisserar, videomodellen genererar pixlarna

```text
Jag har rätt att använda: [konceptbilder, figurer, musik, varumärkesmaterial]. Var manusförfattare och
regissör för en [30] s film där klippen genereras av [videomodell]. Gör först en kontinuitetstabell för
figurerna, första/sista bild per tagning, kamerarörelse, rytm och ljudplan; skriv sedan prompt per
tagning. Logga per tagning: referensbilder, modell och version, antal försök och varför vi valde
det. Klipp ihop, kontrollera kontinuitet, text och ljudsynk. Leverera MP4, storyboard, prompts,
källor, genereringslogg och faktisk kostnad. Redovisa öppet vem som gjorde vad.
```
*Kostnad:* videomodeller (t.ex. Higgsfield/Seedance) är betalda – fråga innan.

## 6. Omgestaltning av befintlig film

```text
Använd min film [sökväg] (som vi har rätt till) som enda bildkälla och gör en version i [stil].
Mät först längd, format, bildfrekvens, ljud och undertexter, och lista vad som inte får ändras
[originalljud/undertexter/längd/identitet/ordning]. Skriv en plan per tidsavsnitt: vad som finns i
originalet, vad den nya bilden blir, vad som måste ritas till eller lagas. Gör först 10 s prov och
kontrollera synk mot ljud och undertexter, gör sedan hela filmen. Leverera MP4 och källkod/projekt;
lista originalets bidrag, externa modeller och manuella steg. Påstå inte att originalets
framträdande, röst eller bild skapats från noll.
```

## 7. Kort trigger för en befintlig skill/motor

```text
Använd projektets [skill/motor] och gör en [längd] s film i [format] för [varumärke/ämne]. Manus och
fakta finns i [sökväg]; licensierade bilder, logga, ljud och typsnitt i [mapp]. Lista först vilka
program, renderare, externa tjänster, mallar och kostnader skillen kommer att använda; kontrollera
fakta och namn i manuset utan att skriva om obekräftade påståenden. Följ skillens flöde: lågupplöst
prov, stickprov på början/mitten/slut av varje tagning och text-/ljudsynk, logga ändringar, exportera
MP4 och redigerbart projekt. Redovisa vad som var mänsklig input, förinstallerad skill och befintligt material.
```
*Golfkuponger:* motsvarar en beställning via `studio` → vald mall i Content Library.
