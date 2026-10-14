"""Skriver library/sounds/LIBRARY.json från listan nedan och ritar en vågformsbild per ljud (library/previews/).
Lägg till nya godkända ljud här och kör: python library/sounds/make_library.py
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import sounds  # noqa: E402

MIXKIT = "Mixkit Sound Effects Free License (reklam ok; får inte ligga i mallar/verktyg – hämtas)"
MIXKIT_MUSIC = "Mixkit Stock Music Free License (reklam ok; får inte ligga i mallar/verktyg – hämtas)"
CC0 = "CC0 (Freesound) – fri användning, ingen attribution"
PIXABAY = "Pixabay Content License – reklam ok, ingen attribution; sprid inte som lösa ljud"
FILM = "GK Årsskiftet (spola tillbaka), godkänd av Jonas 2026-10-13"
FILM2 = "GK Chefen betalar (ingen portal), godkänd av Jonas 2026-10-14"
FILM3 = "GK Spelat den här? (alla banor), godkänd av Jonas 2026-10-14"
# Ljud som används i flera filmer eller bara i en senare film (id -> användning)
USED_IN = {k: FILM + "; " + FILM2 for k in ("sound.smack-dov-trumma", "sound.klocktick", "sound.papper-glid", "sound.bollsus", "music.under-the-sun")}
NEW2 = {"music.comical", "sound.bekraftelse", "sound.dorr-knarr", "sound.syrsor", "sound.mejlnotis", "sound.mobiltryck", "sound.tangenter"}

# id, namn, roll (när det passar), sökord, källa, licens, file|url, md5, cut, nivåtips
S = [
    ("sound.spola-tillbaka", "Spola tillbaka (bandspelare)", "Spola tillbaka / rewind-övergång, VHS, tillbakablick",
     ["spola tillbaka", "rewind", "vhs", "kassett", "band", "övergång", "baklänges"],
     "Mixkit 1088 – Tape rewind cinematic transition", MIXKIT, None, "https://assets.mixkit.co/active_storage/sfx/1088/1088-preview.mp3",
     "b0bc07cba750cc0854178dd2466191f2", {"start": 0.0, "dur": 2.05, "fade_in": 0.03, "fade_out": 0.15},
     "Byggs upp 0,5 s, jämn till 4 s. 2 s-utdraget täcker en spolning. Nivå ~-9 dB RMS (mitt i)."),
    ("sound.larm-anlaggning", "Larm – anläggning (Tjernobyl)", "Larm/varning när något går fel: förbud, för sent, katastrof",
     ["larm", "alarm", "varning", "tjernobyl", "kontrollrum", "siren", "för sent", "förbud"],
     "Mixkit 999 – Facility alarm sound", MIXKIT, None, "https://assets.mixkit.co/active_storage/sfx/999/999-preview.mp3",
     "e79d0df00656856e7bffe31fcb19bf6e", {"start": "onset", "dur": 4.0, "fade_out": 0.4},
     "Loopa utdraget. ~-12 dB under smällen; sänk 18 dB när något annat ska höras (t.ex. gråt)."),
    ("sound.smack-dov-trumma", "Smäll – dov trumma", "Något tungt slår ner (förbudsmärke, GODKÄNT-stämpel, dom)",
     ["smäll", "impact", "slår ner", "trumma", "förbudsmärke", "stämpel", "hit"],
     "Mixkit 565 – Hard horror hit drum", MIXKIT, None, "https://assets.mixkit.co/active_storage/sfx/565/565-preview.mp3",
     "37a7a7369adca9ccb13be5d672bbc9af", {"start": "onset", "pre": 0.005, "dur": 1.4, "fade_out": 0.3},
     "Hjältljud: filmens starkaste (~-3 dB RMS). Musiken tvärdör samtidigt."),
    ("sound.kassettknapp", "Kassettknapp (paus/play)", "Paus och play, knapptryck, bandspelare",
     ["kassett", "knapp", "paus", "play", "klick", "bandspelare", "vhs"],
     "Freesound 423870 – Cassette Tape Button", CC0, "library/sounds/files/kassettknapp_freesound-423870.wav", None, None,
     "Redan utklippt (0,46 s). ~-8 dB RMS."),
    ("sound.boll-i-hal", "Golfboll i hålet", "Bollen trillar i koppen (putt), mål, lyckat",
     ["golf", "putt", "boll i hål", "kopp", "hole in", "green"],
     "Freesound 21878 (inbeeld) – golf_putting.wav", CC0, "library/sounds/files/boll-i-hal_freesound-21878.wav", None, None,
     "Mycket tyst original (-39 dB): placera på ansatsen (~0,4 s in) och nivåsätt ~6 dB över musiken."),
    ("sound.golftraff", "Golfträff", "Klubba träffar bollen, kort skarp träff (även svagt under andra smällar)",
     ["golf", "slag", "träff", "drive", "klubba", "hit"],
     "Pixabay – golf 14 (freesound_community 94167)", PIXABAY, "library/sounds/files/golftraff_pixabay-94167.mp3", None, None,
     "Skarp transient: lägg ett lågpass ~15,5 kHz före limitern, annars toppar AAC över 0 dB."),
    ("sound.papper-riv", "Papper rivs isär", "Något slås igenom/rivs sönder, papper som rivs",
     ["papper", "riva", "rip", "tear", "kalender", "smäll igenom"],
     "Freesound 342541 – Fast Paper Rip", CC0, "library/sounds/files/papper-riv_freesound-342541.wav", None, None,
     "Utklipp 0,33 s. Ersatte en skarp golfträff som smäll ('för oskönt'). ~-11 dB RMS."),
    ("sound.grat-man", "Man gråter", "Gråt, sorg, ledsen figur (tecknat)",
     ["gråt", "gråter", "ledsen", "sorg", "tårar", "crying", "figur"],
     "Pixabay – Crying man effect (peterpiotr, 450354)", PIXABAY, "library/sounds/files/grat-man_pixabay-450354.mp3", None,
     {"start": 0.45, "dur": 2.0, "fade_in": 0.04, "fade_out": 0.03},
     "23 s med flera attacker: 0,45 s (gråten bryter ut), 12,2 s (kraftigast), 18,4 s (snyftande). ~-8 dB RMS."),
    ("sound.bollsus", "Sus – boll mot kameran", "Kort sus före en träff (topp ~0,17 s in)",
     ["sus", "whoosh", "boll", "flyger", "övergång"],
     "Pixabay – whoosh-short", PIXABAY, "library/sounds/files/bollsus_pixabay-whoosh-short.mp3", None, None,
     "Lägg starten där föremålet syns, toppen landar ~0,17 s senare. Svagare än smällen (~-14 dB)."),
    ("sound.kalenderblad", "Kalenderblad vänds", "Ett blad/sida vänds lugnt",
     ["papper", "blad", "sida", "kalender", "vänd"], "Mixkit 1104 – Page turn single", MIXKIT, None,
     "https://assets.mixkit.co/active_storage/sfx/1104/1104-preview.mp3", "44d69cb5bbf8eb789255e9972d58ebff", None, "~3 dB över musiken."),
    ("sound.bladdring", "Snabb bläddring", "Många blad i följd (tiden rusar)",
     ["bläddring", "papper", "kalender", "tid", "snabbt"], "Mixkit 1102 – Fast browsing book paging", MIXKIT, None,
     "https://assets.mixkit.co/active_storage/sfx/1102/1102-preview.mp3", "b0ba9431ce674950678ee16c04c11ada", None, "Bädd ~-4 dB, tona in/ut 0,4/0,8 s."),
    ("sound.papper-snabbriv", "Blad rivs av", "Ett kalenderblad rivs av (de sista dagarna)",
     ["riva", "blad", "kalender", "papper"], "Mixkit 2384 – Paper quick slice", MIXKIT, None,
     "https://assets.mixkit.co/active_storage/sfx/2384/2384-preview.mp3", "ffc673f08ad2154b9a4f465953160a24", None, "Par med klocktick, 1–3 dB över musiken."),
    ("sound.klocktick", "Klocktick", "Tiden går, nedräkning (ett tick per händelse)",
     ["klocka", "tick", "tid", "nedräkning"], "Mixkit 1061 – Clock ticker single", MIXKIT, None,
     "https://assets.mixkit.co/active_storage/sfx/1061/1061-preview.mp3", "2e88a77537a7e2f41db906b0da95c121",
     {"start": "onset", "dur": 0.3, "fade_out": 0.08}, "Kort svans (0,3 s) så det blir tyst när det ska."),
    ("sound.tandsticka", "Tändsticka", "Något tänds/börjar brinna",
     ["eld", "tänd", "tändsticka", "brinner"], "Mixkit 2590 – Fire match lighting", MIXKIT, None,
     "https://assets.mixkit.co/active_storage/sfx/2590/2590-preview.mp3", "31121d5fe4a46b48c98a8a3bd3680c4d",
     {"start": 0.0, "dur": 1.6, "fade_out": 0.5}, ""),
    ("sound.eld-sprak", "Eld som sprakar", "Något brinner (bädd som växer med elden)",
     ["eld", "sprak", "brinner", "brinner inne"], "Mixkit 1330 – Campfire crackles", MIXKIT, None,
     "https://assets.mixkit.co/active_storage/sfx/1330/1330-preview.mp3", "f8bd237ac6f1ad56943836409e495518", None, "Ramp -12 → -2 dB i takt med elden."),
    ("sound.boll-studs", "Bollstuds", "Boll som studsar på gräs",
     ["boll", "studs", "golf", "bounce"], "Mixkit 2073 – Game ball tap", MIXKIT, None,
     "https://assets.mixkit.co/active_storage/sfx/2073/2073-preview.mp3", "df27a3e66ecf2f0b74bf90a4b702c0ce", None, "Andra studsen 2 dB svagare."),
    ("sound.papper-glid", "Papper glider/vänds", "Kort/kupong vänds eller glider",
     ["papper", "kort", "kupong", "vänd", "glid"], "Mixkit 1530 – Paper slide", MIXKIT, None,
     "https://assets.mixkit.co/active_storage/sfx/1530/1530-preview.mp3", "7bb8baa5d61a2a6ae97e63572fc03b01", None, "I nivå med musiken."),
    ("music.running-out-of-time", "Musik: Running Out of Time (130 BPM)", "Spänning/brådska, tiden rinner ut",
     ["musik", "spänning", "brådska", "deadline", "tid", "130 bpm"], "Mixkit musik 77 – Running Out of Time (Ahjay Stelino)", MIXKIT_MUSIC, None,
     "https://assets.mixkit.co/music/77/77.mp3", "a4de927c43ca7609fa91a7655c702bc0", None,
     "Starka slag från 2,299 s (lägg den på första texten). Hårt stopp + 0,1 s tystnad före vändpunkten."),
    ("music.comical", "Musik: Comical (140 BPM)", "Lekfull, smygande, humor – fräcka/roliga filmer",
     ["musik", "rolig", "humor", "fräck", "smyg", "lekfull", "140 bpm"], "Mixkit musik 2 – Comical (Ahjay Stelino)", MIXKIT_MUSIC, None,
     "https://assets.mixkit.co/music/2/2.mp3", "ab405ddcf2a9fa42d2e6e1e1a8e48783", None,
     "Taktstart 0,244 s. Hårt stopp + tick-tack före en vändpunkt (stämpeln), sedan glad musik."),
    ("sound.bekraftelse", "Bekräftelse – klart/köpt", "Något lyckas: köp genomfört, grön bock, godkänt i mobilen",
     ["bekräftelse", "klart", "köpt", "bock", "checkmark", "lyckat", "ui"], "Mixkit 2867 – Confirmation tone", MIXKIT, None,
     "https://assets.mixkit.co/active_storage/sfx/2867/2867-preview.mp3", "38c2f8a1123edfdde20382437cf1c32f", None,
     "Lägg på när bocken ritas klart. ~3 dB över musiken."),
    ("sound.dorr-knarr", "Dörr som knarrar upp", "En dörr öppnas (gärna till något tomt/oväntat)",
     ["dörr", "knarr", "öppnar", "creak", "tomt"], "Mixkit 195 – Creaky door open", MIXKIT, None,
     "https://assets.mixkit.co/active_storage/sfx/195/195-preview.mp3", "3fe48c3ef4fa47b500c140535d6b5f6c", None,
     "Utan musik under – tystnaden efteråt är poängen. ~-12 dB RMS."),
    ("sound.syrsor", "Syrsor – pinsam tystnad", "Komisk tystnad: ingenting här, ingen svarar",
     ["syrsor", "tystnad", "pinsamt", "tomt", "humor", "crickets"], "Mixkit 1788 – Summer crickets loop", MIXKIT, None,
     "https://assets.mixkit.co/active_storage/sfx/1788/1788-preview.mp3", "11a22e229a0a2a8188e9324a0f030ed0",
     {"start": 1.0, "dur": 2.3, "fade_in": 0.25, "fade_out": 0.4}, "Svagt (~-16 dB RMS), direkt efter en dörr eller en fråga."),
    ("sound.mejlnotis", "Mejlnotis", "Ett mejl/meddelande kommer (kvitto, bekräftelse)",
     ["mejl", "notis", "meddelande", "kvitto", "pdf", "mobil"], "Mixkit 2354 – Message pop alert", MIXKIT, None,
     "https://assets.mixkit.co/active_storage/sfx/2354/2354-preview.mp3", "189686648f6f0f20c5dbb1b342d00b09", None, "~1 dB över musiken."),
    ("sound.mobiltryck", "Tryck på mobilskärm", "Fingret trycker på en knapp i mobilen",
     ["tryck", "tap", "klick", "mobil", "knapp", "ui"], "Pixabay – click-soft", PIXABAY, "library/sounds/files/mobiltryck_pixabay-click-soft.mp3", None, None,
     "Lägg på varje tryck, ~2 dB över musiken."),
    ("sound.tangenter", "Skriver på mobilen", "Någon skriver (namn, sökord) – ~1 s",
     ["skriver", "tangenter", "typing", "mobil", "formulär"], "Pixabay – typing", PIXABAY, "library/sounds/files/tangenter_pixabay-typing.mp3", None,
     {"start": "onset", "dur": 1.0, "fade_in": 0.01, "fade_out": 0.08}, "I nivå med musiken."),
    ("music.lifes-a-movie", "Musik: Life's a Movie (episk uppbyggnad)", "Episk uppbyggnad med stort lyft – avslöjande, \"alla banor\", final",
     ["musik", "episk", "uppbyggnad", "lyft", "filmisk", "trailer", "final"], "Mixkit musik 322 – Life's a Movie (Arulo)", MIXKIT_MUSIC, None,
     "https://assets.mixkit.co/music/322/322.mp3", "0332df41ce154529a58c8f04fa1920cc", None,
     "Starta 35,0 s in i spåret: tyst del 37–44 s, lyftet vid ~45 s – lägg lyftet på filmens stora avslöjande."),
    ("music.under-the-sun", "Musik: Under the Sun (120 BPM)", "Lättnad, sol, golf, glatt slut",
     ["musik", "glad", "sol", "golf", "vår", "120 bpm"], "Mixkit musik 859 – Under the Sun (Michael Ramir C.)", MIXKIT_MUSIC, None,
     "https://assets.mixkit.co/music/859/859.mp3", "376303e4efe79bc98da66e425aabf306", None,
     "Taktstart 24,232 s i spåret. Tona ut 0,55 s vid irisen/slutbilden."),
]


def main():
    out = []
    prev = ROOT / "library" / "previews"
    for row in S:
        if len(row) == 10:  # lokal fil: (..., file, None, cut, tips)
            row = row[:7] + (None, None) + row[8:]
        sid, name, role, tags, source, lic, file, url, md5, cut, tips = row
        used = USED_IN.get(sid, FILM3 if sid == "music.lifes-a-movie" else FILM2 if sid in NEW2 else FILM)
        bank = {"role": role, "source": source, "license": lic, "used_in": used, "level": tips}
        if file:
            bank["file"] = file
        else:
            bank["url"], bank["md5"] = url, md5
        if cut:
            bank["cut"] = cut
        still = f"library/previews/{sid}.png"
        item = {
            "id": sid, "name": name, "type": "sound", "medium": "audio", "formats": ["any"], "engine": "python",
            "description": f"{role}. Källa: {source}.", "tags": ["ljud", "godkänt", "ljudbank"] + tags,
            "path": file or "library/sounds/sounds.py",
            "use": f"python library/sounds/sounds.py copy {sid} work/<film>/sfx/{sid.split('.')[-1]}.wav" + (" --cut" if cut else ""),
            "requires": ["ffmpeg", "python"], "cost": "free", "status": "verified", "verified_at": "2026-10-14" if sid in NEW2 or sid == "music.lifes-a-movie" else "2026-10-13",
            "preview": {"video": None, "still": still}, "notes": tips, "bank": bank,
        }
        out.append(item)
    data = {"kit": "sounds", "title": "Ljudbanken – godkända ljud", "source": {"name": "Content Engine", "url": "",
            "license": "Per ljud, se bank.license"}, "items": out}
    (HERE / "LIBRARY.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for item in out:  # vågformsbild från exakt det godkända utdraget
        src = sounds.get(item["id"], cut=bool(item["bank"].get("cut")))
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-filter_complex",
                        "aformat=channel_layouts=mono,showwavespic=s=640x160:colors=0xD6A536", "-frames:v", "1",
                        str(ROOT / item["preview"]["still"])], check=True)
    print(f"{len(out)} ljud -> library/sounds/LIBRARY.json + vågformer i {prev}")


if __name__ == "__main__":
    main()
