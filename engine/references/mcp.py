"""MCP tools for reference videos: take a video that works (a monitored ad or any URL), break it down, and plan our
own, better version for the company. The same tools serve ChatGPT and Claude, so both work the same way."""

from mcp.server.mcpserver import Image
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from engine.mcp_db import database_tool

from . import service
from .models import ReferenceVideo

FLOW = (
    "Referens → vår version. 1) Användaren klistrar in en videolänk (Meta Ad Library, Instagram, TikTok, YouTube, "
    "Facebook eller en direktlänk) → analyze_reference_video. Eller: list_reference_candidates visar bevakade "
    "annonser som gått länge (= fungerar), välj en och skicka dess url. 2) Visa view_reference_sheet och "
    "sammanfatta nedbrytningen: krok, struktur, tempo, ljud, varför den fungerar. 3) plan_our_version för bolaget "
    "(fråga efter vinkel om användaren har en; annars föreslå). Visa planen scen för scen, vad som finns i "
    "mediabanken, vad som ska filmas och vilka fakta som måste verifieras. 4) Fortsätt sedan som vanligt för video: "
    "skills studio, video-regler och ljud (read_ad_skill) – beslutsrunda före full rendering. Lån av grammatik, "
    "aldrig av innehåll: referensens bilder, personer, formuleringar, musik och påståenden kopieras aldrig."
)


def register(mcp, company_for, safe_call):
    read = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)
    paid = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True)

    def reference_for(company_ref: str, reference_id: str) -> ReferenceVideo:
        company = company_for(company_ref)
        ref = ReferenceVideo.objects.filter(pk=reference_id, company=company).select_related("company").first()
        if not ref:
            raise ToolError("Referensen finns inte för det här företaget.")
        return ref

    @mcp.tool(title="Analyze reference video", annotations=paid, description=(
        "START HERE when the user shares a video link or wants 'our version' of an ad/reel. " + FLOW + " Fetches the "
        "video (yt-dlp/direct), stores our own copy, measures cuts/tempo/sound exactly (free) and lets a vision model "
        "watch it with sound (a few öre). Same file twice is reused. Takes 30–120 s; if the client times out, call "
        "list_references and get_reference. Returns the reference with a short breakdown."))
    @database_tool
    def analyze_reference_video(company_ref: str, url: str, model: str = "") -> dict:
        company = company_for(company_ref)
        ref = safe_call(service.process, company, url, model=model)
        return service.serialize(ref)

    @mcp.tool(title="List reference candidates", annotations=read)
    @database_tool
    def list_reference_candidates(company_ref: str, limit: int = 15) -> list[dict]:
        """Monitored competitor ads ranked as references: longest running and active first (an ad that keeps running
        is making money), then EU reach. Each has a url for analyze_reference_video and reference_id if already
        broken down. Not every ad has video; analyze_reference_video says so."""
        return safe_call(service.candidates, company_for(company_ref), limit=max(1, min(limit, 50)))

    @mcp.tool(title="List references", annotations=read)
    @database_tool
    def list_references(company_ref: str, limit: int = 20) -> list[dict]:
        """Reference videos already fetched for the company, newest first, with status and short breakdown."""
        company = company_for(company_ref)
        return [service.serialize(r) for r in ReferenceVideo.objects.filter(company=company)[:max(1, min(limit, 50))]]

    @mcp.tool(title="Get reference", annotations=read)
    @database_tool
    def get_reference(company_ref: str, reference_id: str, adaptation_id: str = "") -> dict:
        """Full breakdown (scene by scene with exact times, text, speech, sound, camera, why it works, what not to
        copy) and measurements. With adaptation_id: also that 'our version' plan."""
        ref = reference_for(company_ref, reference_id)
        data = service.serialize(ref, full=True)
        if adaptation_id:
            match = next((a for a in ref.adaptations if a["id"] == adaptation_id), None)
            if not match:
                raise ToolError("Den versionen finns inte för referensen.")
            data["adaptation"] = match
        return data

    @mcp.tool(title="View reference contact sheet", annotations=read)
    @database_tool
    def view_reference_sheet(company_ref: str, reference_id: str) -> Image:
        """One frame per measured scene with its time, so you and the user can see the reference."""
        ref = reference_for(company_ref, reference_id)
        if not ref.sheet_key:
            raise ToolError("Referensen har ingen kontaktkarta än.")
        return Image(data=safe_call(service._read, ref, ref.sheet_key), format="jpeg")

    @mcp.tool(title="Break reference down again", annotations=paid)
    @database_tool
    def reanalyze_reference(company_ref: str, reference_id: str, model: str, make_current: bool = False) -> dict:
        """Break the same reference down with another vision model (OpenRouter id, e.g. google/gemini-3.1-pro-preview)
        to compare. Every run is kept; make_current=true makes this one the breakdown that plans use."""
        ref = reference_for(company_ref, reference_id)
        return service.serialize(safe_call(service.analyze, ref, model=model, make_current=make_current), full=True)

    @mcp.tool(title="Plan our version", annotations=paid)
    @database_tool
    def plan_our_version(company_ref: str, reference_id: str, angle: str = "", notes: str = "",
                         model: str = "") -> dict:
        """Our version of the reference for this company: same grammar (hook, structure, rhythm, camera, sound), our
        angle, verified facts, media bank, products and recipes. Per scene: what is shown, text, sound and where the
        material comes from (asset_id in the media bank, product image, shot to film, AI scene with model). Also
        facts_to_verify, a to_film list, the closest recipe and risks. A few öre. Run again with another angle for
        alternatives; all are kept on the reference."""
        ref = reference_for(company_ref, reference_id)
        return safe_call(service.plan_our_version, ref, angle=angle, notes=notes, model=model)
