"""The vision model watches a reference video with sound and writes a scene schedule: what happens, how it is shot,
what is said and heard, and why it works. It gets the exact measured cuts, tempo and silence, so its times are
anchored to frames instead of guessed.

Model: REFERENCE_VIDEO_MODEL, else DEFAULT_MODEL. Callers may pass any OpenRouter model id
that accepts video (used to compare models side by side). The reported cost comes from OpenRouter's usage field.
"""

from __future__ import annotations

import base64
import os

from pydantic import BaseModel, Field

VERSION = "reference-breakdown/1"


class Scene(BaseModel):
    id: str = Field(description="Scen-id ur mätningen (s1, s2 …). Slå ihop eller dela bara om mätningen uppenbart har fel.")
    start_s: float
    end_s: float
    shot: str = Field(description="Bildutsnitt och vinkel: närbild, halvbild, helbild, total, POV förarplats, "
                                  "skärminspelning, grafik …")
    camera: str = Field(description="Kamerarörelse: statisk, handhållen, push-in, pan, följer, drönare, zoom …")
    shows: str = Field(description="Vad som syns, konkret: person, miljö, produkt, ljus, väder, tid på dygnet")
    action: str = Field(description="Vad som händer i scenen")
    on_screen_text: str = Field(default="", description="Exakt text på skärmen, annars tomt")
    spoken: str = Field(default="", description="Exakt vad som sägs i scenen, annars tomt")
    sound: str = Field(default="", description="Musik, ljudeffekter, miljöljud, tystnad – och var de slår")
    purpose: str = Field(description="Scenens roll: krok, problem, spänning, avslöjande, bevis, före/efter, "
                                     "demo, socialt bevis, erbjudande, CTA, avsändare …")
    production: str = Field(default="", description="Hur den troligen är gjord: mobil, proffskamera, gimbal, "
                                                    "studio, stock, AI-genererad, grafik/animation")


class Hook(BaseModel):
    first_seconds: str = Field(description="Exakt vad som händer 0–2 s (bild, text, ljud)")
    type: str = Field(description="Typ av krok: problem, fråga, resultat först, överraskning, humor, POV, "
                                  "utmaning, före/efter, stark bild, mönsterbrott …")
    why_it_stops: str = Field(description="Varför man slutar scrolla, en mening")


class Audio(BaseModel):
    voice: str = Field(description="Ingen / person i bild / berättarröst / text-till-tal, och vem det låter som")
    transcript: str = Field(default="", description="Allt som sägs, ordagrant, på originalspråket")
    music: str = Field(description="Finns musik? Genre, stämning, energi, var den bygger och var den bryts")
    sfx: str = Field(default="", description="Ljudeffekter och var de sitter")
    cut_to_music: str = Field(description="Klipps bilden på musikens takt eller betoningar? Hur tydligt?")


class Breakdown(BaseModel):
    observations: str = Field(description="Först: vad du ser och hör i tidsordning, kort. Max 8 meningar.")
    summary: str = Field(description="Vad annonsen är, i en mening")
    format: str = Field(description="Format: produktdemo, POV, före/efter, talking head, UGC, sketch, tutorial, "
                                    "testimonial, montage, skärminspelning … (kombinationer ok)")
    hook: Hook
    structure: list[str] = Field(description="Berättelsens steg i ordning, t.ex. ['Krok: …', 'Problem: …', "
                                             "'Bevis: …', 'Erbjudande: …', 'CTA: …']")
    scenes: list[Scene]
    audio: Audio
    text_style: str = Field(description="Texten på skärmen: typsnittskänsla, storlek, placering, färg, animation, "
                                        "undertexter eller rubriker")
    pacing: str = Field(description="Tempo och rytm: snitt-tid per bild, var det går fort/långsamt och varför")
    cta: str = Field(description="Uppmaning: vad, när och hur (text, röst, knapp, slutkort)")
    claims: list[str] = Field(default_factory=list, description="Påståenden och erbjudanden i annonsen (pris, "
                                                                 "garanti, siffror). Bara för kännedom – kopieras aldrig.")
    why_it_works: list[str] = Field(description="3–6 skäl till att den fungerar (eller inte) som annons")
    mechanics: list[str] = Field(description="Återanvändbara grepp som går att låna utan att kopiera innehållet: "
                                             "krokgrepp, struktur, klippteknik, kameraspråk, ljudgrepp, textgrepp")
    do_not_copy: list[str] = Field(description="Det som är deras och aldrig får kopieras: varumärken, personer, "
                                               "specifika bilder, formuleringar, påståenden, musik")
    production_needs: list[str] = Field(description="Vad som krävs för att göra en egen version: personer, platser, "
                                                    "fordon, produkter, utrustning, tid på dygnet, väder, ljud")
    quality_score: int = Field(ge=1, le=10, description="Hur bra den är som social annons, 1–10")
    quality_note: str = Field(description="En mening: det starkaste och det svagaste")


SYSTEM = (
    "Du är en erfaren reklamfilmare, klippare och performance-kreatör för korta sociala annonser (Reels, TikTok, "
    "Facebook). Du får en referensvideo med ljud från någon annan, plus exakta mätningar av den: klipptider och "
    "scener (bildruteexakta), hur mycket bilden rör sig per scen, tempo i BPM, tystnad och ljudnivå. "
    "Bryt ner videon så att ett annat företag kan göra en egen film med samma grammatik – krok, struktur, rytm, "
    "kameraspråk, ljud – men med eget innehåll.\n"
    "Regler: Använd mätningens scen-id och tider; slå ihop eller dela en scen bara när mätningen uppenbart har fel "
    "(t.ex. en blixt eller övertoning som räknats som klipp), och säg det i observations. Skriv exakt text på skärmen "
    "och exakt vad som sägs. Beskriv bara det du faktiskt ser och hör – hitta inte på. Hör du inget ljud, skriv det. "
    "Var konkret: 'handhållen POV från förarplatsen, mörk skogsväg, vägen syns ca 40 m' – inte 'snygg bild'. "
    "Skriv på svenska; citat på originalspråket."
)


DEFAULT_MODEL = "google/gemini-3.8-flash"  # 2026-10-13 comparison: Flash-Lite missed music and transitions


def default_model() -> str:
    return os.environ.get("REFERENCE_VIDEO_MODEL", "").strip() or DEFAULT_MODEL


def payload_for(measurements: dict, *, title: str = "", author: str = "", context: dict | None = None) -> dict:
    return {
        "reference": {"title": title, "author": author, **(context or {})},
        "measurements": {
            "summary": measurements.get("summary"),
            "probe": measurements.get("probe"),
            "scenes": measurements.get("scenes"),
            "audio": measurements.get("audio"),
        },
        "input": "Hela videon med ljud bifogas (nedskalad kopia, samma tider).",
    }


def run(proxy: bytes, measurements: dict, *, model: str = "", title: str = "", author: str = "",
        context: dict | None = None) -> tuple[dict, dict]:
    """→ (breakdown dict, meta with model and cost_usd). Raises OpenRouterError."""
    from engine.openrouter import _call

    model = model or default_model()
    result, meta = _call(
        model, system=SYSTEM, payload=payload_for(measurements, title=title, author=author, context=context),
        schema=Breakdown, operation="reference_breakdown", max_tokens=12000, temperature=0.2,
        timeout_seconds=240, strict_schema=False,
        videos=["data:video/mp4;base64," + base64.b64encode(proxy).decode("ascii")])
    return {"version": VERSION, **result.model_dump()}, meta
