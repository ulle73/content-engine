"""MCP tools for the review loop: send a video to Discord, read verdicts and the lessons learned."""

from mcp.types import ToolAnnotations

from engine.mcp_db import database_tool

from . import discord, lessons, service
from .models import Lesson, Review


def register(mcp, company_for, safe_call):
    read = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)
    write = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True)

    @mcp.tool(title="Send video for review", annotations=write)
    @database_tool
    def send_for_review(company_ref: str, asset_id: str, title: str, caption: str = "", manifest: dict | None = None,
                        draft_id: str = "", previous_review_id: str = "") -> dict:
        """Post a finished video to the company's Discord review channel with 👍/👎, Ändra, Kommentar and 1–10.
        Always pass `manifest`: {"global": [{"id","type","label"}], "scenes": [{"id","start","end","purpose","text",
        "items": [{"id","type","label","params"}]}]} with the exact Content Library ids used (template, effects,
        transitions, text, sound, AI model per scene). That is how feedback like "effekten vid 0:07 är billig" finds
        the right item and the system learns. If manifest is omitted and draft_id is given, it is built from the brief.
        previous_review_id: set when this is a new version after 'Ändra'."""
        from engine.ad_studio.service import get_draft
        from engine.models import MediaAsset

        from .manifest import from_brief

        company = company_for(company_ref)
        asset = safe_call(MediaAsset.objects.get, pk=asset_id, company=company)
        draft = safe_call(get_draft, company, draft_id) if draft_id else None
        parent = safe_call(Review.objects.get, pk=previous_review_id, company=company) if previous_review_id else None
        if not manifest and draft:
            manifest = from_brief(draft.brief)
        review = safe_call(service.create, company, asset, title=title, caption=caption, manifest=manifest,
                           ad_draft=draft, parent=parent)
        safe_call(discord.send, review)
        return service.serialize(review)

    @mcp.tool(title="List reviews", annotations=read)
    @database_tool
    def list_reviews(company_ref: str, status: str = "", limit: int = 10) -> list[dict]:
        """Videos sent for review with status (pending/approved/rejected/changes/superseded), 1–10 and every comment
        with its interpretation. Status 'changes' = the owner pressed Ändra: make a new version that fixes the
        comment (see fix_now in feedback.interpreted.points) and send it with previous_review_id."""
        reviews = Review.objects.filter(company=company_for(company_ref)).prefetch_related("feedback")
        if status:
            reviews = reviews.filter(status=status)
        return [service.serialize(r) for r in reviews[:min(limit, 50)]]

    @mcp.tool(title="List lessons", annotations=read)
    @database_tool
    def list_lessons(company_ref: str, include_inactive: bool = False) -> list[dict]:
        """What the system has learned from the owner's ratings and comments for this company. Read before
        proposing ideas or choosing library items, and follow it."""
        company = company_for(company_ref)
        qs = Lesson.objects.filter(company=company) if include_inactive else lessons.active(company)
        return [lessons.serialize(lesson) for lesson in qs[:100]]

    @mcp.tool(title="Forget lesson", annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False,
                                                                 openWorldHint=False))
    @database_tool
    def forget_lesson(company_ref: str, lesson_id: int) -> dict:
        """Deactivate a lesson the owner says is wrong (it can be re-learned from new feedback)."""
        lesson = safe_call(Lesson.objects.get, pk=lesson_id, company=company_for(company_ref))
        lesson.active = False
        lesson.save(update_fields=["active"])
        return lessons.serialize(lesson)
