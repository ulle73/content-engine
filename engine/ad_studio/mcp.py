"""Ad Studio MCP tools: the idea-engine flow from first sentence to production."""

from mcp.types import ToolAnnotations

from engine.mcp_db import database_tool

from . import blueprints, service, skills

FLOW = (
    "Ad Studio-flöde: 1) read_ad_skill för golfkuponger-brand och golfkuponger-friskvard (eller relevant skill). "
    "2) start_ad_brief med användarens budskap. 3) Följ next_question: max tre frågor åt gången, alltid med "
    "färdiga förslag. 4) Föreslå tre olika vinklar. 5) search_ad_assets per scenroll, visa kandidater, låt användaren "
    "välja eller ladda upp. 6) Remotion (gratis) eller Higgsfield (kostar): rekommendera och visa kostnad. 7) För Remotion: "
    "get_ad_template_blueprint och bygg storyboarden på exakt de scenerna. 8) update_ad_brief efter varje beslut. "
    "9) När användaren säger kör: lock_ad_brief och sedan produce_ad. Hitta aldrig på fakta, och lägg varje påstående i "
    "facts med källa."
)


def register(mcp, company_for, run_for, user_for, safe_call):
    read = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)
    write = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False)

    @mcp.tool(title="List ad skills", annotations=read)
    @database_tool
    def list_ad_skills(company_ref: str) -> list[dict]:
        """Skills (brand, domain knowledge) to read before designing an ad. """
        company_for(company_ref)
        return skills.available()

    @mcp.tool(title="Read ad skill", annotations=read)
    @database_tool
    def read_ad_skill(company_ref: str, name: str) -> str:
        """Read one skill's full instructions. Read golfkuponger-brand plus the relevant domain skill before proposing ideas."""
        company_for(company_ref)
        return safe_call(skills.read, name)

    @mcp.tool(title="Start ad brief", annotations=write, description="Start the guided ad flow. " + FLOW)
    @database_tool
    def start_ad_brief(company_ref: str, message: str = "", title: str = "") -> dict:
        draft = safe_call(service.start_draft, company_for(company_ref), user_for(), message=message, title=title)
        return dict(service.serialize(draft), flow=FLOW, skills=skills.available())

    @mcp.tool(title="List ad briefs", annotations=read)
    @database_tool
    def list_ad_briefs(company_ref: str) -> list[dict]:
        """Ongoing and locked ad drafts for this company."""
        return service.list_drafts(company_for(company_ref))

    @mcp.tool(title="Get ad brief", annotations=read)
    @database_tool
    def get_ad_brief(company_ref: str, draft_id: str) -> dict:
        """Current brief with `missing`, `next_question`, `problems` and `lockable`."""
        return service.serialize(safe_call(service.get_draft, company_for(company_ref), draft_id))

    @mcp.tool(title="Update ad brief", annotations=write)
    @database_tool
    def update_ad_brief(company_ref: str, draft_id: str, changes: dict, expected_revision: int) -> dict:
        """Save decisions. `changes` keys replace whole top-level AdBrief fields: message, objective
        (awareness/consideration/conversion/retargeting), audience, offer, campaign, angle {title, hook, why_it_works},
        assets [{asset_id, role, origin library/upload/generate, note, generation_prompt}], engine {engine
        remotion/higgsfield/hybrid, remotion_template_id, estimated_cost_sek, cost_approved}, formats, duration_s,
        scenes [{id, purpose hook/problem/solution/how/proof/offer/cta, duration_s, asset_id, on_screen_text <=8 words,
        voiceover, motion, transition_in}], copy {primary_text, headline, cta_label, landing_url}, facts [{claim, source,
        verified}], forbid, variants. Only set cost_approved or fact verified=true when the user confirmed it."""
        draft = safe_call(
            service.update_draft, company_for(company_ref), draft_id, changes=changes, expected_revision=expected_revision
        )
        return service.serialize(draft)

    @mcp.tool(title="Get ad template blueprint", annotations=read)
    @database_tool
    def get_ad_template_blueprint(company_ref: str, template_id: str) -> dict:
        """Scene skeleton (ids, seconds, asset slots, text slots) for a Remotion template. Build AdBrief.scenes from it.
        Templates: list_motion_templates. Friskvård: friskvard-portal-ad, friskvard-direct-ad."""
        company_for(company_ref)
        return safe_call(blueprints.blueprint, template_id)

    @mcp.tool(title="Search ad assets", annotations=read)
    @database_tool
    def search_ad_assets(company_ref: str, query: str = "", role: str = "", kind: str = "", limit: int = 12) -> dict:
        """Find images/videos in the company bank by meaning (tags, description). role: hook/footage/screen/product/
        proof/end_card. Show 2-3 candidates per role with view_media and let the user choose."""
        return service.search_assets(company_for(company_ref), query=query, role=role, kind=kind, limit=limit)

    @mcp.tool(title="List untagged media", annotations=read)
    @database_tool
    def list_untagged_media(company_ref: str, limit: int = 20) -> list[dict]:
        """Images/videos without tags. Look at each with view_media, then tag_media_asset."""
        return service.untagged_assets(company_for(company_ref), limit=limit)

    @mcp.tool(title="Tag media asset", annotations=write)
    @database_tool
    def tag_media_asset(company_ref: str, asset_id: str, description: str, tags: list[str], roles: list[str],
                        theme: str = "", season: str = "", mood: str = "", source: str = "",
                        verified: bool = False) -> dict:
        """Save what an image/video shows after looking at it with view_media. Describe only what is visible.
        roles: hook/footage/screen/product/proof/end_card/logo/other. verified=true only if the user confirmed."""
        obj = safe_call(service.tag_asset, company_for(company_ref), asset_id, description=description, tags=tags,
                        roles=roles, theme=theme, season=season, mood=mood, source=source, verified=verified)
        return {"asset_id": asset_id, "tags": service.serialize_tags(obj)}

    @mcp.tool(title="Lock ad brief", annotations=write)
    @database_tool
    def lock_ad_brief(company_ref: str, draft_id: str, expected_revision: int) -> dict:
        """Freeze the agreed brief when the user says go. Fails with exact reasons if anything is missing or wrong."""
        return service.serialize(
            safe_call(service.lock_draft, company_for(company_ref), draft_id, expected_revision=expected_revision)
        )

    @mcp.tool(title="Reopen ad brief", annotations=write)
    @database_tool
    def reopen_ad_brief(company_ref: str, draft_id: str) -> dict:
        """Unlock a locked brief to change it (not after production started)."""
        return service.serialize(safe_call(service.reopen_draft, company_for(company_ref), draft_id))

    @mcp.tool(title="Produce ad", annotations=write)
    @database_tool
    def produce_ad(company_ref: str, draft_id: str, idempotency_key: str) -> dict:
        """Build exactly the locked brief. Remotion: creates a Motion project (then preview/approve/render with the
        motion tools). Higgsfield assets to generate are returned as requests for the reviewed media tools."""
        return safe_call(service.produce, company_for(company_ref), user_for(), draft_id, key=idempotency_key)
