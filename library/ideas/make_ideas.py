"""Idébanken: premisser för hela filmer – nivån ovanför tekniker (krok/struktur) och utförande (mallar/effekter).
AI-slop uppstår på idénivån, så varje ny film börjar här (skills/ny-video). Skriver library/ideas/LIBRARY.json och en
beskrivning per idé (library/ideas/<slug>.md).

Lägg till eller uppdatera: ändra IDEER nedan och kör
  python library/ideas/make_ideas.py && python library/tools/build_catalog.py

Fält: id (ide.<slug>), namn, genre (ett av GENRER – tre förslag i samma runda har alltid olika genre), premiss (filmen
i en mening), overraskning (vad som gör att den inte är generisk), kansla, golf (vår vridning / användning),
stack (hur vi bygger: html-playwright, hyperframes, remotion, blender, filmat, ai-video), blender (vad Blender skulle
lyfta – eller None när 3D inte tillför något), material (vad som behövs; ✓ = finns hos oss), tekniker (teknik.* i
teknikbanken), bolag, medium, bevis (egen film eller referens), anvand (filmer som använt idén, med datum),
omdome (Jonas 👍/👎 med datum och kommentar – skrivs efter varje val så att banken lär sig).

Status: verified = vi har gjort en film på idén som Jonas godkänt. unverified = oprövad eller underkänd i utförandet
(se omdome) – fortfarande en idé, men visa ett rörelsetest först.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

GENRER = {
    "objekt-metafor": "ett vardagsföremål bär budskapet (kalender, timglas, kvitto)",
    "tidsresa": "spola tillbaka, framtid, andra chans",
    "sketch": "figurer eller personer spelar upp en situation",
    "fraga-igenkanning": "tittaren känner igen något och svarar i huvudet",
    "parodi-hyllning": "lånar en känd bild, film eller genre och vrider den",
    "3d-varld": "en byggd miniatyr- eller 3D-värld man färdas genom",
    "forklaring-ui": "riktiga skärmar och steg visar hur något fungerar",
    "lokalt-tilltal": "talar direkt till en plats eller grupp",
    "chatt-samtal": "berättelsen sker i en chatt, ett mejl eller ett samtal",
    "lanseringstrailer": "filmisk reveal av något nytt",
    "spel-utmaning": "tittaren ska hitta, gissa eller klara något",
    "nedrakning": "tiden som rinner ut är hela filmen",
    "dokumentar": "allvarlig dokumentärform på ett vardagligt ämne",
    "nyhet": "nyhetssändning, breaking, väderprognos",
    "recept-guide": "instruktion i en lånad form (recept, bruksanvisning, IKEA-ritning)",
    "asmr-makro": "närbilder, ljud och taktila detaljer",
    "pov": "kameran är tittarens egna ögon och händer",
    "fore-efter": "två tillstånd ställs mot varandra",
    "karta-resa": "en linje eller resa över en karta",
    "produkt-premium": "produkten som fysiskt föremål i studioljus",
    "karusell-panorama": "karusellens slides bildar en sammanhängande bild",
}

EGEN = lambda film, datum: {"typ": "egen film", "film": film, "godkänd": datum}


def I(id, namn, genre, premiss, overraskning, kansla, golf, stack, material, *, blender=None, tekniker=(),
      bolag="golfkuponger", medium="video", bevis=None, anvand=(), omdome=(), status="unverified", formats=("9:16",)):
    assert genre in GENRER, f"{id}: okänd genre {genre}"
    return dict(id=id, namn=namn, genre=genre, premiss=premiss, overraskning=overraskning, kansla=kansla, golf=golf,
                stack=list(stack), blender=blender, material=list(material), tekniker=list(tekniker), bolag=bolag,
                medium=medium, bevis=bevis, anvand=list(anvand), omdome=list(omdome), status=status,
                formats=list(formats))


IDEER = [
    # ---------- egna filmer (bevisade eller prövade) ----------
    I("ide.rivkalendern", "Rivkalendern till 31 december", "objekt-metafor",
      "En rivkalender rivs dag för dag mot 31 december – friskvårdsbidraget brinner inne när sista bladet faller.",
      "Deadlinen blir fysisk och hörbar i stället för en text.", "brådska", "Friskvårdsbidragets deadline 31/12.",
      ["html-playwright"], ["✓ rivkalender-grafik (gk-arsskifte)", "✓ Spotlight-slutbild"],
      blender="Ett riktigt pappersblock som rivs i 3D med ljus och skuggor skulle göra rivningen taktil.",
      bevis=EGEN("work/gk-arsskifte (v1)", "2026-10"), anvand=[{"film": "gk-arsskifte v1", "datum": "2026-10"}],
      status="verified"),
    I("ide.spola-tillbaka", "Spola tillbaka – andra chansen", "tidsresa",
      "Vi ser hur det går när man glömmer bidraget, bilden spolas tillbaka och samma dag spelas om med golf.",
      "Tittaren ser misstaget innan det händer.", "lättnad", "Glömt friskvårdsbidrag → använt på golf.",
      ["html-playwright"], ["✓ gk-arsskifte spola"], tekniker=["teknik.spola-tillbaka-andra-chans"],
      bevis=EGEN("work/gk-arsskifte (spola)", "2026-10"), anvand=[{"film": "gk-arsskifte spola", "datum": "2026-10"}],
      status="verified"),
    I("ide.chefen-betalar", "Låt chefen betala din golf", "sketch",
      "Chefen-figuren betalar motvilligt men glatt golfen – friskvårdsbidraget som arbetsgivarens gåva.",
      "Ett återkommande tecknat persongalleri i stället för stockfoto.", "skadeglädje, värme",
      "Budskapet ”Låt chefen betala din golf”.", ["html-playwright"],
      ["✓ Chefen-modulen (library/templates/golfkuponger-chefen)", "✓ Tourleif"], tekniker=[],
      bevis=EGEN("work/gk-chefen", "2026-10"), anvand=[{"film": "gk-chefen", "datum": "2026-10"}], status="verified"),
    I("ide.spelat-den-har", "Spelat den här?", "fraga-igenkanning",
      "Kända banor blinkar förbi som en fråga, sedan en vägg av 300+ banor och utmaningen ”hur många klarar du?”.",
      "Tittaren svarar själv i huvudet – igenkänning före budskap.", "nyfikenhet, stolthet",
      "300+ banor, bocka av i appen.", ["html-playwright"], ["✓ banfoton (KLUBBAR/)", "✓ musik E1"],
      tekniker=["teknik.fragor-som-krok", "teknik.vagg-av-allt"],
      bevis=EGEN("work/gk-banor", "2026-10"), anvand=[{"film": "gk-banor", "datum": "2026-10"}], status="verified"),
    I("ide.skriet-31-december", "Skriet, 31 december", "parodi-hyllning",
      "Munchs Skriet med Tourleif – paniken när man inser att bidraget går ut i morgon.",
      "Ett känt konstverk blir en golfskämt-reaktion.", "igenkänning, humor", "Deadline 31/12.",
      ["html-playwright"], ["✓ Tourleif skrik-pose"], tekniker=["teknik.konstverk-hyllning"],
      bevis=EGEN("work/gk-konstverk", "2026-10"), anvand=[{"film": "gk-konstverk", "datum": "2026-10"}],
      status="verified"),
    I("ide.miniatyr-sverige", "Miniatyr-Sverige", "3d-varld",
      "En resa genom ett miniatyr-Sverige där varje område har sina banor, från Skåne och norrut.",
      "Hela utbudet blir en leksaksvärld man vill utforska.", "förundran", "300+ banor över hela landet.",
      ["blender"], ["✓ Blender-scenen (work/gk-miniatyr)", "foton per bana (be om underlag)"],
      blender="Bärs helt av Blender: ljus, djup och miniatyrkänsla går inte att få platt.",
      tekniker=[], bevis=EGEN("work/gk-miniatyr (v4)", "2026-10-18"),
      anvand=[{"film": "gk-miniatyr v4", "datum": "2026-10-18"}], status="verified"),
    I("ide.sa-funkar-det", "Så funkar det – tre steg", "forklaring-ui",
      "Riktiga skärmar och riktiga golfare visar stegen köp → aktivera → spela, i tempo som ClassPass.",
      "Visar produkten i stället för att beskriva den; tempot gör en instruktion underhållande.", "trygghet",
      "Köpflödet: sajten/portalen → kod via mejl → aktivera i appen → saldo.", ["html-playwright", "hyperframes"],
      ["✓ appens skärmar (_material/app-2026-11)", "riktiga golfare i bild (filmat eller VIDEOS/)"],
      blender="3D-iPhone med riktiga skärmar och kamerafärd runt telefonen gör stegen premium.",
      tekniker=["teknik.riktigt-flode-i-mobil"], bevis=EGEN("work/gk-sa-funkar-det (v3)", "2026-10-22"),
      anvand=[{"film": "gk-sa-funkar-det v3", "datum": "2026-10-22"}], status="verified", formats=("9:16", "16:9")),
    I("ide.golfare-i-stad", "Golfare i [stad]?", "lokalt-tilltal",
      "”Golfare i Göteborg?” över ett banfoto från en närliggande klubb – tilltal till en ort.",
      "Känns skriven för just mig; den bästa Meta-annonsen hittills.", "igenkänning",
      "Lokala banor per stad.", ["html-playwright"], ["✓ banfoton per klubb", "✓ mallen golfare-i-stad"],
      bevis=EGEN("golfare-i-stad (Stockholm m.fl.)", "2026-10-28"),
      anvand=[{"film": "golfare-i-stad", "datum": "2026-10-28"}], status="verified"),
    I("ide.imessage-kollegan", "Kollegan i iMessage", "chatt-samtal",
      "Ett iMessage-samtal där kollegan avslöjar hur hen får golfen betald.",
      "Tittaren läser någon annans chatt – nyfikenheten gör resten.", "humor, nyfikenhet",
      "Friskvårdsbidrag via kollegan.", ["hyperframes"], ["✓ mallen imessage-samtal", "✓ Jonas selfie"],
      tekniker=[], bevis=EGEN("work/gk-sugar-daddy", "2026-11-13"),
      anvand=[{"film": "gk-sugar-daddy", "datum": "2026-11-13"}], status="unverified"),
    I("ide.app-reveal", "Nya appen – reveal", "lanseringstrailer",
      "En filmisk lanseringstrailer där appens delar lyfts fram en i taget runt en 3D-iPhone.",
      "Behandlar en golfapp som en stor teknikpremiär.", "förväntan", "Nya Golfkuponger-appen.",
      ["html-playwright"], ["✓ 3D-iPhone (telefon3d.js)", "✓ appens skärmar", "musik (val pågår)"],
      blender="Riktig produktrendering av telefonen med reflexer och studioljus i hero-scenerna.",
      tekniker=["teknik.app-reveal-trailer", "teknik.ringportal-kapitelbyte"],
      bevis=EGEN("work/gk-ny-app-reveal", "2026-11"), anvand=[{"film": "gk-ny-app-reveal", "datum": "2026-11-26"}],
      status="unverified"),
    I("ide.hitta-faran", "Hitta faran i mörkret", "spel-utmaning",
      "Tittaren letar efter det dolda rådjuret i mörkret – sedan tänds extraljusen och det syns direkt.",
      "Tittaren gör själv jobbet och upplever produktens nytta.", "spänning, aha", "FAIV extraljus.",
      ["python"], ["✓ före/efter-bilder från NTH"], bolag="faiv",
      bevis=EGEN("work/faiv-extraljus", "2026-10-24"), anvand=[{"film": "faiv-extraljus", "datum": "2026-10-24"}],
      status="verified"),
    I("ide.kor-du-den-har", "Kör du den här?", "fraga-igenkanning",
      "Bilmodeller blinkar förbi som en fråga, sedan en vägg av 60+ modeller med grillkit.",
      "Samma form som Spelat den här? – fungerar i en annan bransch.", "igenkänning", "FAIV grillkit.",
      ["html-playwright"], ["✓ NTH-bilder"], bolag="faiv", tekniker=["teknik.fragor-som-krok", "teknik.vagg-av-allt"],
      bevis=EGEN("work/faiv-kor-du-den-har", "2026-10-24"), anvand=[{"film": "faiv-kor-du-den-har", "datum": "2026-10-24"}],
      status="unverified"),
    I("ide.dagar-kvar-blink", "7 dagar kvar – blink", "nedrakning",
      "En platt grönt↔guld-växling med texten som fyller bilden: X dagar kvar.",
      "Så enkel att den sticker ut i flödet.", "brådska", "Deadline 31/12.", ["html-playwright"],
      ["✓ mallen golfkuponger-blink"], bevis=EGEN("blink-serie", "2026-11"),
      anvand=[{"film": "blink-serie", "datum": "2026-11"}], status="unverified"),
    I("ide.gissa-banan", "Gissa banan", "spel-utmaning",
      "En bana visas bit för bit – gissa vilken innan den avslöjas.", "Tittaren tävlar mot sig själv.",
      "nyfikenhet", "300+ banor.", ["html-playwright"], ["✓ banfoton"],
      blender="En flygning över banan i 3D (från höjddata/foton) gör avslöjandet filmiskt.",
      omdome=[{"datum": "2026-10-15", "av": "Jonas", "betyg": "👎",
               "kommentar": "Underkänd i utförandet: snurr → för snabb utzoom. Idén i sig ej prövad igen."}],
      status="unverified"),
    I("ide.panorama-karusell", "Panorama över slides", "karusell-panorama",
      "Karusellens slides bildar en sammanhängande bild – bollen flyger genom alla.",
      "Man måste svepa för att se helheten.", "nyfikenhet", "Karusell på Instagram.", ["html-playwright"],
      ["✓ gk-panorama"], tekniker=["teknik.panorama-over-slides"], medium="carousel",
      bevis=EGEN("work/gk-panorama", "2026-10-14"), anvand=[{"film": "gk-panorama", "datum": "2026-10-14"}],
      status="verified", formats=("4:5",)),

    # ---------- oprövade genrer (bredd – visa ett rörelsetest innan de väljs) ----------
    I("ide.naturdokumentar", "Golfaren i sitt habitat", "dokumentar",
      "En viskande naturfilmsröst följer den sällsynta kontorsgolfaren som äntligen använder sitt friskvårdsbidrag.",
      "Allvarlig form på ett vardagligt ämne ger humor utan skämt.", "humor", "Friskvårdsbidraget.",
      ["filmat", "html-playwright"], ["filmat material eller VIDEOS/ (golfare)", "berättarröst (ElevenLabs/inspelad)"],
      blender=None),
    I("ide.breaking-news", "Breaking: bidrag brinner inne", "nyhet",
      "En nyhetssändning med ticker och grafik rapporterar live om alla friskvårdsbidrag som snart går förlorade.",
      "Nyhetsgrafiken är så igenkännbar att budskapet känns akut.", "brådska, humor", "Deadline 31/12.",
      ["html-playwright"], ["nyhetsgrafik (byggs)", "✓ banfoton som 'live-bilder'"],
      blender="3D-studio och roterande nyhetslogga i öppningen.", tekniker=[]),
    I("ide.level-up", "Golfrundan som spel – level 1 till 3", "spel-utmaning",
      "Stegen till golfen är banor i ett tv-spel: level 1 köp, level 2 aktivera, level 3 första tee.",
      "En instruktion som känns som underhållning; progress-mätaren håller kvar tittaren.", "lek, framsteg",
      "Instruktion i tre steg (köp → aktivera → spela).", ["html-playwright", "hyperframes"],
      ["✓ appens skärmar", "pixel/spelgrafik (byggs)", "✓ Tourleif som spelfigur"],
      blender="Låg-poly 3D-golfbana som spelvärld gör spelkänslan premium."),
    I("ide.receptet", "Receptet på en golfsommar", "recept-guide",
      "En matlagningsvideo där ingredienserna är stegen: en kod, en app, en bana – blanda och servera.",
      "Instruktion i en lånad, mysig form.", "värme", "Instruktion i tre steg.", ["html-playwright", "filmat"],
      ["köksbänk (filmat eller 3D)", "✓ appens skärmar"],
      blender="Köksbänk i studioljus med koden som 'ingrediens' i makro."),
    I("ide.asmr-unboxing", "Unboxing av koden", "asmr-makro",
      "Koden i mejlet 'packas upp' som en premiumprodukt – papper, folie, ljudet när appen tänds.",
      "Gör något digitalt fysiskt och taktilt.", "lust, tillfredsställelse", "Köp → kod via mejl → aktivera.",
      ["blender"], ["riktiga ASMR-ljud (ljudbanken)", "✓ appens skärmar"],
      blender="Bärs av Blender: förpackning, folie, makro och skärpedjup."),
    I("ide.vaderprognos", "Golfprognosen", "nyhet",
      "En väderpresentatör visar högtryck över 300 banor och 'hög risk för golf' i helgen.",
      "Kartgrafiken gör utbudet konkret per region.", "humor", "Banor per region.", ["html-playwright"],
      ["Sverigekarta (byggs)", "✓ klubbarnas positioner"], blender=None, tekniker=["teknik.folj-linjen"]),
    I("ide.kontorsstol-tee", "Från kontorsstolen till första tee", "fore-efter",
      "Samma rörelse matchas mellan kontoret och banan – stolen snurrar och blir en sving.",
      "Matchklippet gör förvandlingen fysisk.", "längtan", "Friskvård = golf.", ["filmat", "ai-video"],
      ["två matchade klipp (filmat eller AI)", "✓ banfoton"], blender=None),
    I("ide.pov-telefonen", "POV: från soffan till tee", "pov",
      "Tittarens egna händer köper, aktiverar och betalar greenfee – kameran är dina ögon hela vägen.",
      "Tittaren är huvudpersonen; stegen blir upplevda, inte förklarade.", "trygghet, lust",
      "Instruktion i tre steg.", ["filmat", "html-playwright"],
      ["inspelade POV-klipp med telefon (saknas)", "✓ appens skärmar för skärminlägg"],
      blender="3D-telefon i handen för scener som inte kan filmas."),
    I("ide.guldkortet", "Guldkortet", "produkt-premium",
      "Golfkupongen som ett fysiskt guldkort i studioljus – vänds, glänser, landar på en green.",
      "Ger en digital tjänst ett premiumföremål.", "status", "Golfkuponger som gåva/premium.", ["blender"],
      ["✓ logga (SVG)", "kortdesign (byggs)"], blender="Bärs av Blender: metall, reflexer, makro."),
    I("ide.linjen-over-sverige", "Linjen över Sverige", "karta-resa",
      "En linje dras från bana till bana över Sverigekartan och ritar till slut loggan.",
      "Utbudet blir en resa som slutar i varumärket.", "förundran", "300+ banor.", ["html-playwright"],
      ["✓ klubbarnas positioner", "Sverigekarta (byggs)"], tekniker=["teknik.folj-linjen"],
      blender="Terräng i 3D med kameran som följer linjen."),
]


def md(i):
    lines = [f"# {i['namn']}", "", f"**Genre:** {i['genre']} – {GENRER[i['genre']]}  ", f"**Bolag:** {i['bolag']}  ",
             f"**Status:** {i['status']}", "", f"**Premiss:** {i['premiss']}", "",
             f"**Varför den inte är generisk:** {i['overraskning']}", "", f"**Känsla:** {i['kansla']}", "",
             f"**Golfvridning / användning:** {i['golf']}", "", f"**Så bygger vi den:** {', '.join(i['stack'])}", "",
             f"**Blender:** {i['blender'] or 'tillför inget – håll det platt'}", "", "**Material:**"]
    lines += [f"- {m}" for m in i["material"]] or ["- –"]
    if i["tekniker"]:
        lines += ["", "**Tekniker:** " + ", ".join(f"`{t}`" for t in i["tekniker"])]
    if i["bevis"]:
        lines += ["", f"**Bevis:** {json.dumps(i['bevis'], ensure_ascii=False)}"]
    if i["anvand"]:
        lines += ["", "**Använd i:** " + ", ".join(f"{a['film']} ({a['datum']})" for a in i["anvand"])]
    if i["omdome"]:
        lines += ["", "**Omdöme:**"] + [f"- {o['datum']} {o['av']} {o['betyg']}: {o['kommentar']}" for o in i["omdome"]]
    return "\n".join(lines) + "\n"


def main():
    items = []
    for i in IDEER:
        slug = i["id"].split(".", 1)[1]
        (HERE / f"{slug}.md").write_text(md(i), encoding="utf-8")
        items.append({
            "id": i["id"], "name": i["namn"], "type": "idea", "medium": i["medium"], "formats": i["formats"],
            "engine": "none",
            "description": f"[{i['genre']}] {i['premiss']} Varför: {i['overraskning']} Passar: {i['golf']}",
            "tags": ["idé", i["genre"], i["kansla"], i["bolag"], *i["stack"], *(["blender"] if i["blender"] else [])],
            "path": f"library/ideas/{slug}.md",
            "use": f"Läs library/ideas/{slug}.md. Riktning i skills/ny-video; storyboard via scripts/storyboard.py.",
            "status": i["status"], "verified_at": (i["bevis"] or {}).get("godkänd") if i["status"] == "verified" else None,
            "ide": {k: i[k] for k in ("genre", "premiss", "overraskning", "kansla", "golf", "stack", "blender", "material",
                                     "tekniker", "bolag", "bevis", "anvand", "omdome")},
        })
    data = {"kit": "ideas", "title": "Idébanken – premisser för hela filmer",
            "source": {"name": "Content Engine", "url": "", "license": "Egen beskrivning"},
            "genrer": GENRER, "items": items}
    (HERE / "LIBRARY.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(items)} idéer i {len({i['genre'] for i in IDEER})} genrer -> library/ideas/LIBRARY.json")


if __name__ == "__main__":
    main()
