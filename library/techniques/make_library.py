"""Teknikbanken: bevisade tekniker/metoder för video och karuseller (krokar, retention, vändningar, CTA, struktur …).
Skriver library/techniques/LIBRARY.json + en beskrivning per teknik (library/techniques/<id>.md).

Lägg till en teknik: en ny rad i TEKNIKER nedan (se skills/teknik), kör
  python library/techniques/make_library.py && python library/tools/build_catalog.py

Fält: id (teknik.<slug>), namn, roll (krok/retention/vändning/bevis/cta/struktur/övergång/text), medium (video/carousel),
kort (en mening), hur (vad som händer, steg), varför (psykologin), tajming, tecknat (så bygger vi det i kod), filmat
(så spelar vi in det), golfkuponger (konkret idé för oss), taggar, bevis (källa: länk/kreatör/likes/datum eller egen
godkänd film), preview (bara egen bild – aldrig kreatörens video/bilder), exempel (våra mallar/filmer som använder den).
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MAVITA = {"källa": "https://www.instagram.com/reel/DeKwHHlPu0i/", "kreatör": "Maria Valeria Simonelli (@mavasimonellis)",
          "likes": 7921, "kommentarer": 79, "datum": "2026-10-06", "lokal_kopia": "work/references/instagram-DeKwHHlPu0i/",
          "notering": "Utbildande reel om hooks – 6 klipp, snitt 3,1 s per klipp. Vi lånar greppen, aldrig bilder/formuleringar/ljud."}
EGEN = lambda film, datum="2026-10-14": {"källa": film, "kreatör": "Golfkuponger (egen film)", "godkänd": f"Jonas {datum}"}

TEKNIKER = [
    # ---------- från referenser ----------
    dict(id="teknik.ord-knapps-bort", namn="Ett ord knäpps bort och vänder budskapet", roll="krok", medium=["video", "carousel"],
         kort="En rad med ett negerande ord ('INTE') står i bild – en gest knäpper bort ordet och budskapet vänder.",
         hur="1) Raden visas komplett ('This is NOT a hook'). 2) Personen/figuren knäpper, pekar eller sveper på ordet. "
             "3) Ordet flyger ut ur bild (rotation + rörelseoskärpa), de andra orden glider ihop. Karusell: slide 1 med ordet, slide 2 utan.",
         varför="Tittaren hinner läsa påståendet och blir överraskad när det ändras – en mikroförvåning de första 2 sekunderna "
                "som skapar nyfikenhet. Fysisk interaktion med text känns 'gjord för dig'.",
         tajming="Raden ≥ läsregeln (~2 s) innan ordet åker; bortknäppet 0,2–0,3 s; ny rad står 1–1,5 s.",
         tecknat="Tourleif (expr 'lurig') knäpper med fingret; ordet = eget <span> som animeras ut; övriga ord flyttas med samma easing.",
         filmat="Personen gör en tydlig knäppgest mot tomrummet bredvid huvudet; texten läggs efteråt synkad till bildrutan där fingret träffar.",
         golfkuponger="'FRISKVÅRD ÄR INTE GOLF' → INTE knäpps bort → 'FRISKVÅRD ÄR GOLF'. Eller 'GOLF ÄR INTE FÖR ALLA' → 'GOLF ÄR FÖR ALLA'.",
         taggar=["hook", "krok", "text", "gest", "negation", "överraskning", "kinetisk typografi"], bevis=MAVITA),
    dict(id="teknik.text-poppar-pa-gest", namn="Text poppar upp på en gest", roll="krok", medium=["video"],
         kort="Texten dyker upp exakt när personen knäpper/pekar/klappar – som om gesten skapade den.",
         hur="Personen gör en gest mot en tom yta; texten skalar in med studs på gestens bildruta, med ett kort pop-ljud.",
         varför="Orsak–verkan fångar ögat; tittaren förstår direkt vart den ska titta och att videon är 'gjord'.",
         tajming="Texten in inom 1–2 bildrutor efter gesten; studs 0,25 s; ljud på samma bildruta (aldrig före).",
         tecknat="Tourleif pekar (expr 'glad'/'blinkar'); text in med eBack vid exakt tid.", filmat="Spela in gesten mot en lugn bakgrund med luft bredvid personen för texten.",
         golfkuponger="Hook: knäpp → '3 SAKER OM FRISKVÅRDSBIDRAGET'. Eller pekar → 'VISSTE DU DET HÄR?'",
         taggar=["hook", "krok", "text", "gest", "pop", "studs"], bevis=MAVITA),
    dict(id="teknik.bilden-trycks-isar", namn="Bilden trycks isär med händerna", roll="retention", medium=["video"],
         kort="Personen 'trycker' bildens kanter inåt/utåt med händerna – svarta kanter kommer in och texten står mellan händerna.",
         hur="1) Personen höjer händerna mot bildens kanter. 2) Bilden beskärs (svart in från sidorna) i takt med händerna. "
             "3) Texten centreras i det kvarvarande fönstret.",
         varför="Bryter bildens 'fjärde vägg' – oväntad formändring som återställer uppmärksamheten mitt i videon (retention).",
         tajming="Rörelsen 0,4–0,6 s; håll 1,5–2 s; släpp tillbaka.", tecknat="Tourleif med händerna utåt; maska/beskär scenen med två svarta rektanglar som följer händerna.",
         filmat="Händerna mot kamerans kanter, stilla kamera (stativ) så att maskningen blir ren.",
         golfkuponger="Mitt i en tipsfilm: händerna trycker isär → 'DETTA MISSAR ALLA'.",
         taggar=["retention", "övergång", "fjärde väggen", "beskärning", "gest"], bevis=MAVITA),
    dict(id="teknik.text-foljer-personen", namn="Texten följer med personen", roll="retention", medium=["video"],
         kort="Texten sitter fast vid personen (bröstet, bredvid huvudet) och följer med när hen går in i bild eller rör sig.",
         hur="Personen går in i bild framför en lugn vägg; texten glider med i samma fart (spårning) eller sitter på kroppen.",
         varför="Texten blir en del av scenen i stället för ett lager ovanpå – ser påkostat ut och håller blicken på personen.",
         tajming="Hela promenaden 2–4 s; texten läsbar hela tiden (läsregeln).",
         tecknat="Text i samma <g>-transform som figuren.", filmat="Lugn bakgrund, personen rör sig i sidled; spåra med verktyget för rörelse/embedded-captions (text bakom/vid motivet).",
         golfkuponger="Golfare går över green, texten 'FÖRSTA RUNDAN = FRISKVÅRD' följer med.",
         taggar=["retention", "tracking", "spårning", "text", "rörelse", "embedded captions"], bevis=MAVITA),
    dict(id="teknik.cirkel-cta-redigeringsvy", namn="Avslutning: cirkel + CTA i redigeringsvy", roll="cta", medium=["video"],
         kort="Bilden krymper till en cirkel med ansiktet; CTA:n ('spara & följ') skrivs fram i en textruta med markeringshandtag och muspekare.",
         hur="1) Helbild → cirkelmask som krymper mot centrum (svart runt). 2) En textruta med streckad markering ritas, "
             "texten skrivs fram, muspekaren klickar.",
         varför="Ser ut som att man tittar in i redigeringen – ärligt/'creator'-känsla som gör CTA:n mindre säljig; cirkeln personifierar avsändaren.",
         tajming="Krympning 0,5 s; CTA ≥ läsregeln; klick sist.", tecknat="Tourleif i cirkel; textruta + pekare i SVG.",
         filmat="Avslutningsbild av personen; resten grafik.", golfkuponger="Cirkel med Tourleif: 'SPARA & FÖLJ FÖR FLER GOLFTIPS' – före slutbilden.",
         taggar=["cta", "avslutning", "follow", "spara", "redigering", "muspekare", "cirkel"], bevis=MAVITA),
    dict(id="teknik.samma-rad-ny-lek", namn="Samma rad – ny visuell lek var 2–3 s", roll="struktur", medium=["video"],
         kort="Hela videon upprepar samma korta rad, men varje klipp visar ett nytt sätt att animera den.",
         hur="Välj en rad (t.ex. 'This is a hook'). Klipp 1–6: ny miljö/vinkel + ny textlek (gest, bortknäpp, tryck isär, följ person, cirkel).",
         varför="Tittaren vill se 'nästa trick' – tydlig mönsterbrytning var 2–3 s utan att budskapet blir rörigt. Bra för sparningar (lärande).",
         tajming="6 klipp à 2–4 s (snitt ~3 s); samma textstil genom hela.", tecknat="Tourleif i olika poser/miljöer, samma rad.",
         filmat="En inspelningsdag: 5–6 korta tagningar med olika gester mot samma tomma yta.",
         golfkuponger="'GOLF FÖR FRISKVÅRDSBIDRAGET' i sex varianter (dörr, mobil, green, chefen, kupong, cirkel-CTA).",
         taggar=["struktur", "retention", "lista", "lärande", "mönsterbrytning", "sparningar"], bevis=MAVITA),
    # ---------- våra egna godkända filmer ----------
    dict(id="teknik.spola-tillbaka-andra-chans", namn="Fel utfall → paus → spola tillbaka → rätt utfall", roll="struktur", medium=["video"],
         kort="Visa först vad som händer om man inte agerar, pausa, spola tillbaka filmen och visa samma situation med rätt val.",
         hur="1) Varv 1 slutar dåligt (förbudsmärke, gråt). 2) ❚❚ + 'Det här behöver inte hända dig'. 3) ◀◀ hela filmen baklänges. "
             "4) ▶ markera var vi landar, 2–3 lugna steg, rätt utfall.",
         varför="Förlustaversion först (känslan), sedan lösningen – tittaren upplever konsekvensen och lättnaden. Spolningen är ett visuellt wow.",
         tajming="Varv 1 ~10 s, paus 3,5 s (läsregeln), spolning 2 s, markera landningen ~1 s.",
         tecknat="Mall golfkuponger.template.arsskifte-spola (partPause/partRewind/partPlay).", filmat="Spela in två slut på samma scen; spolning i efterhand.",
         golfkuponger="Använd i Årsskiftet – spola tillbaka; fungerar för alla 'gör det i tid'-budskap.",
         taggar=["struktur", "spola tillbaka", "rewind", "andra chansen", "före/efter", "förlustaversion"],
         bevis=EGEN("work/gk-arsskifte (spola)", "2026-10-13"), preview="library/previews/golfkuponger.transition.spola-tillbaka.jpg",
         exempel=["golfkuponger.template.arsskifte-spola", "golfkuponger.transition.spola-tillbaka"]),
    dict(id="teknik.las-golf-tas-ifran", namn="Ge det goda – ta det ifrån en", roll="vändning", medium=["video"],
         kort="Låt tittaren känna det goda (golfbanan, 2–3 s, 'ååh golf') innan det tas ifrån hen med ett hårt stopp.",
         hur="Lugn vacker bild + glad musik → förbudsmärke/stopp slår ner, musiken tvärdör, rött larm.",
         varför="Kontrasten gör förlusten fysisk; utan den sköna stunden först blir stoppet bara ett stopp.",
         tajming="Det goda ≥ 2,5–3 s (Jonas: 'ååh golf'), stoppet slår ner på 0,25 s.",
         tecknat="golfkuponger.effect.forbud-larm.", filmat="Vacker banbild + grafiskt stopp ovanpå.",
         golfkuponger="Allt som brinner inne/tar slut: årsskiftet, kampanjslut.",
         taggar=["vändning", "förlust", "stopp", "förbud", "kontrast", "för sent"],
         bevis=EGEN("work/gk-arsskifte (spola)"), preview="library/previews/golfkuponger.effect.forbud-larm.jpg",
         exempel=["golfkuponger.effect.forbud-larm"]),
    dict(id="teknik.dorr-till-ingenting", namn="Dörren till ingenting", roll="krok", medium=["video", "carousel"],
         kort="En dörr/knapp märkt med det tittaren väntar sig ('FÖRMÅNSPORTAL') öppnas – bakom finns bara en tegelvägg och syrsor.",
         hur="Figuren öppnar dörren, dammpuff, tegelvägg + spindelnät, figuren blir förvånad, tystnad med syrsor – sedan lösningen.",
         varför="Igenkänd frustration som humor; tystnaden (syrsor) är skämtet och gör lösningen efteråt välkommen.",
         tajming="Öppning 0,6 s, tom vägg + syrsor ~2 s, sedan lösningen.", tecknat="partDoor i golfkuponger.template.chefen-betalar.",
         filmat="Riktig dörr som öppnas mot en vägg/garderob.", golfkuponger="'Ingen förmånsportal på jobbet?' (godkänd).",
         taggar=["krok", "humor", "tomt", "syrsor", "frustration", "problem"], bevis=EGEN("work/gk-chefen"),
         preview="library/previews/teknik.dorr-till-ingenting.jpg", exempel=["golfkuponger.template.chefen-betalar"]),
    dict(id="teknik.riktigt-flode-i-mobil", namn="Riktigt köpflöde i en tecknad mobil", roll="bevis", medium=["video"],
         kort="Visa det riktiga flödet (sajtens skärmar) i en tecknad mobil – kameran följer fingret, zoomar när något skrivs.",
         hur="Riktiga helsidesbilder från sajten; tryck med krusning, mjuk scroll, sidbyte, inzoomning på fältet, grön bock, mejlnotis med pdf.",
         varför="Bevisar att det är enkelt ('så här gör du') utan att hitta på gränssnitt; tecknad ram håller ihop stilen.",
         tajming="Ett steg per 0,6–1,2 s; tryck alltid inom safe zones.", tecknat="golfkuponger.scene.mobilflode-riktig-sajt.",
         filmat="Skärminspelning i stående format (riktig mobil).", golfkuponger="Köp direkt på golfkuponger.se (godkänd).",
         taggar=["bevis", "så gör du", "ui", "mobil", "köpflöde", "enkelt"], bevis=EGEN("work/gk-chefen"),
         preview="library/previews/golfkuponger.scene.mobilflode-riktig-sajt.jpg", exempel=["golfkuponger.scene.mobilflode-riktig-sajt"]),
    dict(id="teknik.vagg-av-allt", namn="Från en till alla – väggen", roll="bevis", medium=["video", "carousel"],
         kort="Börja på ett exempel, bläddra allt snabbare, zooma ut till en vägg av ALLA (banor/produkter) som bildar loggan.",
         hur="3 hjältebilder med frågor → accelererande bläddring → utzoom från sista bilden till väggen → bockar poppar → logga.",
         varför="Mängd visad i stället för påstådd ('300+') – överväldigande på ett bra sätt, och loggan knyter ihop allt.",
         tajming="Hjältar ~2 s/st, bläddring 3 s (0,3 s → 1 bildruta), utzoom 1,75 s.", tecknat="work/gk-banor (banor.js, prep.py, mosaik_alla.py).",
         filmat="Riktiga bilder krävs (alla klubbars bilder i work/_material/klubbar).", golfkuponger="'Spelat den här?' (godkänd).",
         taggar=["bevis", "mängd", "mosaik", "vägg", "utzoom", "alla", "logga"], bevis=EGEN("work/gk-banor"),
         preview="library/previews/teknik.vagg-av-allt.jpg"),
    dict(id="teknik.fragor-som-krok", namn="'Spelat den här? Eller den här?'", roll="krok", medium=["video", "carousel"],
         kort="Direkta ja/nej-frågor över starka bilder, en per 2 s – tittaren svarar tyst i huvudet och fastnar.",
         hur="Fråga 1 över bild 1, snabb panorering, 'ELLER DEN HÄR?' över bild 2 … plats-etikett under texten.",
         varför="Frågor aktiverar tittaren (självtest); igenkänning ('den har jag spelat!') ger kommentarer.",
         tajming="Läsregeln per fråga (~2 s); panorering 0,24 s.", tecknat="Fungerar även tecknat.", filmat="Starka banbilder.",
         golfkuponger="'Spelat den här?' (godkänd).", taggar=["krok", "fråga", "engagemang", "kommentarer", "igenkänning"],
         bevis=EGEN("work/gk-banor"), preview="library/previews/teknik.spelat-den-har-fragor.jpg"),
    dict(id="teknik.konstverk-hyllning", namn="Hyllning till ett känt konstverk", roll="krok", medium=["video", "carousel"],
         kort="Återskapa ett känt (fritt) konstverk med vår figur – igenkänningen stoppar scrollen, sedan bryts verket upp till verkligheten.",
         hur="Verket ritas i kod (aldrig nedladdat), figuren i verkets pose, verket rivs/öppnas till riktiga bilder.",
         varför="Omedelbar igenkänning + överraskning (vår figur i verket); delbart.",
         tajming="Verket 5–6 s med text, rivningen på ett ljudslag.", tecknat="work/gk-konstverk (Skriet).",
         filmat="–", golfkuponger="Skriet den 31 december (godkänd). Bara verk där konstnären dog för >70 år sedan.",
         taggar=["krok", "konst", "parodi", "igenkänning", "delbart", "public domain"], bevis=EGEN("work/gk-konstverk"),
         preview="library/previews/teknik.konstverk-hyllning.jpg"),
]


def bevis(t):
    """bevis är en dict eller en lista med dicts (flera reels med samma teknik)."""
    return t["bevis"] if isinstance(t["bevis"], list) else [t["bevis"]]


def md(t):
    b = t["bevis"]
    bev = "\n".join(f"- {k}: {v}" for k, v in b.items())
    ex = ", ".join(f"`{e}`" for e in t.get("exempel", [])) or "–"
    return f"""# {t['namn']}  (`{t['id']}`)

**Roll:** {t['roll']} · **Medium:** {', '.join(t['medium'])}

{t['kort']}

## Så går den till
{t['hur']}

## Varför den fungerar
{t['varför']}

## Tajming
{t['tajming']}

## Så bygger vi den
- **Tecknat:** {t['tecknat']}
- **Filmat:** {t['filmat']}

## Idé för Golfkuponger
{t['golfkuponger']}

## Bevis
{bev}

Används i: {ex}
"""


def main():
    items = []
    for t in TEKNIKER:
        slug = t["id"].split(".", 1)[1]
        (HERE / f"{slug}.md").write_text(md(t), encoding="utf-8")
        prev = t.get("preview")
        items.append({
            "id": t["id"], "name": t["namn"], "type": "technique", "medium": t["medium"][0],
            "formats": ["9:16", "4:5", "1:1"] if "carousel" in t["medium"] else ["9:16", "any"], "engine": "none",
            "description": f"[{t['roll']}] {t['kort']} Varför: {t['varför']}",
            "tags": ["teknik", t["roll"]] + t["medium"] + t["taggar"], "path": f"library/techniques/{slug}.md",
            "use": f"Läs library/techniques/{slug}.md. Golfkuponger: {t['golfkuponger']}",
            "requires": [], "cost": "free", "status": "verified" if prev else "unverified",
            **({"verified_at": next((b["godkänd"].replace("Jonas ", "") for b in bevis(t) if "godkänd" in b), "")} if prev else {}),
            "preview": {"video": None, "still": prev} if prev else None,
            "notes": "Bevisad hos andra – bygg en egen demo första gången (då blir den verified)." if not prev else "Godkänd i egen film.",
            "teknik": {"roll": t["roll"], "medium": t["medium"], "tajming": t["tajming"], "bevis": t["bevis"],
                       "exempel": t.get("exempel", [])},
        })
    data = {"kit": "techniques", "title": "Teknikbanken – bevisade tekniker och metoder",
            "source": {"name": "Content Engine", "url": "", "license": "Egen beskrivning; referensvideor bara lokalt (work/references)"},
            "items": items}
    (HERE / "LIBRARY.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(items)} tekniker -> library/techniques/LIBRARY.json")


if __name__ == "__main__":
    main()
