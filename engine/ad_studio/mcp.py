"""Ad Studio MCP tools: the idea-engine flow from first sentence to production."""

from mcp.server.mcpserver import Image
from mcp.types import ToolAnnotations

from engine import product_catalog
from engine.mcp_db import database_tool
from engine.review import lessons

from . import blueprints, library, service, skills

FLOW = (
    "Ad Studio-flöde. Var proaktiv: föreslå hellre en komplett plan som användaren justerar än att ställa många frågor. "
    "0) Börja aldrig från noll: sök i Content Library med search_content_library (mallar, effekter, övergångar, "
    "textbehandlingar, karusellstilar, prompts) och föreslå 2–3 färdiga, snygga kombinationer att utgå från. "
    "För video: sök först type='recipe' (produktionsrecept per bolag med scener, filmlista-id:n, effekter och "
    "valfria AI-uppgraderingar; get_content_library_item ger hela receptet) och type='model' (model playbooks: "
    "vilken AI-modell per scentyp och hur den promptas). Recepten är förslag, inte regler, och fungerar med riktigt "
    "material utan betald AI. "
    "Video av eget material går snabbast via receptet: plan_cut_from_recipe (gratis, inga sidoeffekter) väljer "
    "klipp ur mediabanken per scen (filmlista-id som fa-m1/gk-o1), fyller text med bara verifierade fakta och "
    "tillämpar ägarens lärdomar. Visa planen och listan `missing` (vad som ska filmas/laddas upp och taggas med "
    "tag_media). När planen är klar: render_recipe (klipper i molnet, postas i Discord med AI-granskning), följ med "
    "get_cut_job. Justera via overrides i stället för att skriva klippspecen för hand; render_cut bara för specialfall. "
    "Stilen är fri; brand-skillen är ett utgångsläge, inte regler. "
    "Läs alltid list_lessons först: det är ägarens tidigare betyg och kommentarer (t.ex. 'undvik glitch-övergången'). "
    "Följ dem, och sökträffar med our_feedback visar vad som gillats/ogillats. "
    "Visar annonsen en produkt eller bana: hitta den med search_products och hämta de riktiga bilderna med "
    "use_product_images (laddas ner först då). Hitta aldrig på hur en produkt ser ut. "
    "1) read_ad_skill: studio (bibliotekets arbetssätt), ad-studio (hur samtalet leds), golfkuponger-brand och relevant domänskill. "
    "2) start_ad_brief med användarens budskap. "
    "3) Max 3 frågor, bara det som verkligen saknas (next_question), alltid med färdiga svarsförslag. "
    "4) Föreslå tre olika vinklar och rekommendera en. "
    "5) Om användaren har en referensvideo i mediabanken: visa den med preview_ad_reference_video, analysera endast "
    "rörelsegrammatik (tempo, kamera, transitioner, typografi) och spara med set_ad_reference_profile. Kopiera aldrig "
    "referensens claims, loggor, personer eller produktidentitet. "
    "6) Remotion (gratis, mall) eller Higgsfield (kostar): rekommendera och visa kostnad. För Remotion: "
    "get_ad_template_blueprint och bygg scenerna exakt på mallens scen-id och tider. "
    "7) suggest_scene_assets och visa sedan kandidaterna med show_ad_images (numrerade), så användaren svarar "
    "'ta 2 och 5'. Bilder som användaren klistrar in i chatten sparas med add_ad_image. "
    "8) update_ad_brief med hela förslaget och visa preview_ad_storyboard. Iterera tills användaren är nöjd. "
    "9) Vid 'kör': lock_ad_brief, sedan produce_ad, sedan render_motion_project (preview). "
    "10) När previewn är klar: review_ad_render. Granska varje bildruta mot brand-skillens checklista, "
    "visa resultatet och föreslå rättningar innan approve_motion_preview och final. "
    "Varje svar innehåller studio_url: ge användaren länken 'Öppna i studion' när något är lättare att klicka "
    "(välja bilder, ladda upp, ändra text per scen, se storyboarden stort). Samma utkast, samma brief. "
    "Fakta: läs list_ad_facts. Använd bara påståenden med status verified, och lägg dem i facts med deras fact_id. "
    "Saknas något, föreslå det med propose_ad_fact och be användaren verifiera i faktabanken. "
    "Du kan aldrig verifiera själv. Hitta aldrig på fakta."
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

    @mcp.tool(title="Search content library", annotations=read)
    @database_tool
    def search_content_library(company_ref: str, query: str = "", type: str = "", format: str = "",
                               medium: str = "", kit: str = "", verified_only: bool = False,
                               limit: int = 15) -> dict:
        """Find ready-made, good-looking starting points before creating anything. Searches every template,
        effect, transition, text treatment, carousel style, skill, prompt, production recipe and AI-model playbook
        in the Content Library.
        type: template/scene/effect/transition/text/caption/grade/background/carousel/skill/prompt/sound/tool/
        recipe/model.
        format: 9:16/1:1/4:5/16:9. medium: video/carousel/image/audio/text. Verified items with previews rank first.
        Propose 2-3 combinations (base template + effects + text + sound) and let the user pick."""
        company = company_for(company_ref)
        return library.search(query, type=type, format=format, medium=medium, kit=kit,
                              verified_only=verified_only, limit=limit, feedback=lessons.library_feedback(company))

    @mcp.tool(title="Get content library item", annotations=read)
    @database_tool
    def get_content_library_item(company_ref: str, item_id: str) -> dict:
        """Full details for one Content Library item: how to use it, requirements, cost, preview and file path."""
        company_for(company_ref)
        return safe_call(library.get, item_id)

    @mcp.tool(title="Search products", annotations=read)
    @database_tool
    def search_products(company_ref: str, query: str = "", limit: int = 20) -> list[dict]:
        """Products (FAIV) or golf courses (Golfkuponger) synced from the company's own webshop, with every
        image URL. Words match name, SKU, category and description. Run sync_products if the list is empty."""
        return [product_catalog.serialize(p) for p in product_catalog.search(company_for(company_ref), query, limit=min(limit, 50))]

    @mcp.tool(title="Use product images", annotations=write)
    @database_tool
    def use_product_images(company_ref: str, product_id: int, image_indexes: list[int] | None = None) -> dict:
        """Download chosen images (indexes into image_urls; default all) of one product into the media bank and
        return their asset_ids for the brief. Only images that are actually used get stored."""
        from engine.models import CatalogProduct

        company = company_for(company_ref)
        product = safe_call(CatalogProduct.objects.get, pk=product_id, company=company)
        assets = safe_call(product_catalog.materialize, product, indexes=image_indexes)
        return dict(product_catalog.serialize(product), stored_asset_ids=[str(a.pk) for a in assets])

    @mcp.tool(title="Sync products", annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True))
    @database_tool
    def sync_products(company_ref: str) -> dict:
        """Re-read the product catalog (data + image URLs, no image downloads) from the company's own webshop."""
        return safe_call(product_catalog.sync, company_for(company_ref))

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
        scenes [{id, purpose hook/problem/solution/how/proof/offer/cta, duration_s, asset_id, on_screen_text (short reads best; no hard limit),
        voiceover, motion, transition_in}], copy {primary_text, headline, cta_label, landing_url}, facts [{claim, source,
        fact_id}], forbid, variants. Facts get their verified status from the fact bank; you cannot verify. Only set
        cost_approved when the user confirmed the cost."""
        draft = safe_call(
            service.update_draft, company_for(company_ref), draft_id, changes=changes,
            expected_revision=expected_revision, human=False,
        )
        return service.serialize(draft)

    @mcp.tool(title="Preview ad reference video", annotations=read)
    @database_tool
    def preview_ad_reference_video(company_ref: str, asset_id: str, frames: int = 6) -> Image:
        """Show 3–12 evenly sampled frames from a company-owned reference video. Free/local.
        Use it to infer only creative mechanics such as motion intensity, camera style, transition family,
        typography behavior, beat density and color behavior; never copy source claims or identity."""
        return Image(
            data=safe_call(service.reference_video_sheet, company_for(company_ref), asset_id, frames=frames),
            format="jpeg",
        )

    @mcp.tool(title="Set ad reference profile", annotations=write)
    @database_tool
    def set_ad_reference_profile(
        company_ref: str,
        draft_id: str,
        profile: dict,
        expected_revision: int,
    ) -> dict:
        """Persist an allow-listed Reference Profile after visually reviewing the reference.
        Allowed profile fields: source_asset_id, label, motion_intensity low/medium/high,
        camera_style locked/push/orbit/dolly/handheld/macro/aerial/mixed,
        transition_family cuts/soft/dynamic/mixed,
        typography_behavior none/minimal/kinetic/editorial/bold,
        beat_density sparse/medium/dense,
        motion_preset legacy/soft/snappy/weighty/editorial,
        color_behavior brand/natural/muted/high-contrast, optional bpm 40–220 and notes."""
        draft = safe_call(
            service.set_reference_profile,
            company_for(company_ref),
            draft_id,
            profile=profile,
            expected_revision=expected_revision,
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

    @mcp.tool(title="List ad facts", annotations=read)
    @database_tool
    def list_ad_facts(company_ref: str) -> dict:
        """The company's fact bank: claims allowed in ads, each verified / unverified / blocked by a human.
        Only verified claims may appear on screen; reference them in the brief as facts[].fact_id."""
        company = company_for(company_ref)
        facts = service.list_facts(company)
        from django.conf import settings
        from django.urls import reverse

        url = settings.APP_URL.rstrip("/") + reverse("engine:ad_facts", kwargs={"workspace_id": company.pk})
        return {"facts": facts, "fact_bank_url": url}

    @mcp.tool(title="Propose ad fact", annotations=write)
    @database_tool
    def propose_ad_fact(company_ref: str, claim: str, source: str, note: str = "") -> dict:
        """Add a claim to the fact bank as UNVERIFIED, with where it comes from. A human verifies it in the studio."""
        fact = safe_call(service.propose_fact, company_for(company_ref), claim=claim, source=source, note=note)
        return service.serialize_fact(fact)

    @mcp.tool(title="Produce ad", annotations=write)
    @database_tool
    def produce_ad(company_ref: str, draft_id: str, idempotency_key: str) -> dict:
        """Build exactly the locked brief. Remotion: creates a Motion project (then preview/approve/render with the
        motion tools). Higgsfield assets to generate are returned as requests for the reviewed media tools."""
        return safe_call(service.produce, company_for(company_ref), user_for(), draft_id, key=idempotency_key)
