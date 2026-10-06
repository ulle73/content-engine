"""Ad Studio MCP tools: the idea-engine flow from first sentence to production."""

from mcp.server.mcpserver import Image
from mcp.types import ToolAnnotations

from engine.mcp_db import database_tool

from . import blueprints, service, skills

FLOW = (
    "Ad Studio-flöde. Var proaktiv: föreslå hellre en komplett plan som användaren justerar än att ställa många frågor. "
    "1) read_ad_skill: ad-studio (hur samtalet leds), golfkuponger-brand och relevant domänskill. "
    "2) start_ad_brief med användarens budskap. "
    "3) Max 3 frågor, bara det som verkligen saknas (next_question), alltid med färdiga svarsförslag. "
    "4) Föreslå tre olika vinklar och rekommendera en. "
    "5) Remotion (gratis, mall) eller Higgsfield (kostar): rekommendera och visa kostnad. För Remotion: "
    "get_ad_template_blueprint och bygg scenerna exakt på mallens scen-id och tider. "
    "6) suggest_scene_assets och visa sedan kandidaterna med show_ad_images (numrerade), så användaren svarar "
    "'ta 2 och 5'. Bilder som användaren klistrar in i chatten sparas med add_ad_image. "
    "7) update_ad_brief med hela förslaget och visa preview_ad_storyboard. Iterera tills användaren är nöjd. "
    "8) Vid 'kör': lock_ad_brief, sedan produce_ad, sedan render_motion_project (preview). "
    "9) När previewn är klar: review_ad_render. Granska varje bildruta mot brand-skillens checklista, "
    "visa resultatet och föreslå rättningar innan approve_motion_preview och final. "
    "Varje svar innehåller studio_url: ge användaren länken 'Öppna i studion' när något är lättare att klicka "
    "(välja bilder, ladda upp, ändra text per scen, se storyboarden stort). Samma utkast, samma brief. "
    "Hitta aldrig på fakta. Varje påstående läggs i facts med källa."
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

    @mcp.tool(title="Show ad images", annotations=read)
    @database_tool
    def show_ad_images(company_ref: str, asset_ids: list[str], title: str = "") -> Image:
        """Visual picker: up to 12 images/videos as one numbered sheet (1..n in the given order). Show it and let the
        user answer with numbers. Keep your own number→asset_id mapping from the order you passed."""
        return Image(data=safe_call(service.show_images, company_for(company_ref), asset_ids, title), format="jpeg")

    @mcp.tool(title="Suggest scene assets", annotations=read)
    @database_tool
    def suggest_scene_assets(company_ref: str, draft_id: str) -> dict:
        """Best image-bank candidates per scene (no asset repeated as first choice). Follow with show_ad_images."""
        return safe_call(service.suggest_scene_assets, company_for(company_ref), draft_id)

    @mcp.tool(title="Add ad image", annotations=write)
    @database_tool
    def add_ad_image(company_ref: str, draft_id: str, image_base64: str, role: str, description: str,
                     tags: list[str], expected_revision: int, theme: str = "", source: str = "") -> dict:
        """Save an image the user pasted in chat into the media bank, tag it (describe only what is visible) and attach
        it to the brief in one step. role: hook/footage/screen/product/proof/end_card/other. Accepts base64 or data URL."""
        draft, asset = safe_call(service.add_image, company_for(company_ref), user_for(), draft_id,
                                 image_base64=image_base64, role=role, description=description, tags=tags,
                                 expected_revision=expected_revision, theme=theme, source=source)
        return dict(service.serialize(draft), added_asset_id=str(asset.pk))

    @mcp.tool(title="Preview ad storyboard", annotations=read)
    @database_tool
    def preview_ad_storyboard(company_ref: str, draft_id: str) -> Image:
        """The whole ad as one image before rendering: every scene with its picture, on-screen text, timing, safe-zone
        guides (yellow) and any rule problems in red. Show it after each storyboard change. Free."""
        return Image(data=safe_call(service.storyboard_image, company_for(company_ref), draft_id), format="jpeg")

    @mcp.tool(title="Review ad render", annotations=read)
    @database_tool
    def review_ad_render(company_ref: str, draft_id: str) -> Image:
        """Keyframes of the latest finished render with safe-zone guides. Check each frame against the brand checklist:
        text inside the guides and readable, max 8 words, hook visible at once, real UI not distorted, logo/end card
        correct, premium Scandinavian feel. Report findings and propose fixes before approving."""
        return Image(data=safe_call(service.review_image, company_for(company_ref), draft_id), format="jpeg")

    @mcp.tool(title="Produce ad", annotations=write)
    @database_tool
    def produce_ad(company_ref: str, draft_id: str, idempotency_key: str) -> dict:
        """Build exactly the locked brief. Remotion: creates a Motion project (then preview/approve/render with the
        motion tools). Higgsfield assets to generate are returned as requests for the reviewed media tools."""
        return safe_call(service.produce, company_for(company_ref), user_for(), draft_id, key=idempotency_key)
