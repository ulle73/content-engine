"""MCP tools for cloud editing: plan a cut from a production recipe and the media bank, send it to the HyperFrames
renderer on GitHub Actions, follow the job, and tag own footage with shot-list ids (docs/FILMLISTA.md)."""

from mcp.types import ToolAnnotations

from engine.mcp_db import database_tool

from . import footage, planner, service


def register(mcp, company_for, safe_call):
    read = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)
    write = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True)
    tag = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False)

    @mcp.tool(title="Plan cut from recipe", annotations=read)
    @database_tool
    def plan_cut_from_recipe(company_ref: str, recipe_id: str, format: str = "9:16",  # noqa: A002
                             overrides: dict | None = None) -> dict:
        """START HERE for video from own footage. Plans a finished cut from a production recipe
        (search_content_library type='recipe'; the id without the "recipe." prefix, e.g. faiv-dark-to-light-reveal)
        and the company's media bank. No side effects, free. Returns {"ready", "spec" (cut/v1 for render_cut),
        "missing": [{"scene", "footage_ids", "hint"}] (what to film/upload and tag, with shot ids from the shot list),
        "pending_downloads" (product images fetched on render), "choices" (which file per scene and why), "notes"
        (fact safety, lessons from the owner's reviews that were applied, shortened scenes), "warnings"}.
        Show the user the missing list in plain Swedish and ask them to film/upload; tag uploads with tag_media.
        Facts ({fact:Fn}) only appear when verified in the fact bank; otherwise the recipe's safe wording is used.
        overrides (all optional): {"title", "caption", "placeholders": {"car_model": "Volvo XC60"},
        "product_id": <catalog id> | "product_query": "grillkit volvo", "music_asset_id": "<audio uuid>" | "" (none),
        "music_volume": 0–1, "fps": 30, "scenes": {"s1": {"asset_id", "text", "trim_start_s", "duration_s",
        "transition_in", "effects", "text_style", "text_position", "fit", "audio", "skip": true}}}."""
        company = company_for(company_ref)
        return safe_call(planner.plan_cut, company, recipe_id, format=format, overrides=overrides)

    @mcp.tool(title="Render recipe", annotations=write)
    @database_tool
    def render_recipe(company_ref: str, recipe_id: str, format: str = "9:16",  # noqa: A002
                      overrides: dict | None = None, allow_missing: bool = False) -> dict:
        """Plan the recipe (as plan_cut_from_recipe, but product images are downloaded into the media bank) and send
        the cut to the cloud renderer. Refuses when scenes lack material unless allow_missing=true (then those scenes
        are left out). Returns {"plan", "job"}; follow the job with get_cut_job. When done it is posted to the
        company's Discord review channel with an AI critique line, unless the quality gate holds it back (AI score
        under 7 or mostly still images; see quality_gate in get_cut_job). Free (GitHub Actions)."""
        company = company_for(company_ref)
        plan, job = safe_call(planner.render_recipe, company, recipe_id, format=format, overrides=overrides,
                              allow_missing=allow_missing)
        return {"plan": plan, "job": service.serialize(job)}

    @mcp.tool(title="Tag media with shot ids", annotations=tag)
    @database_tool
    def tag_media(company_ref: str, asset_id: str, footage_ids: list[str], description: str = "") -> dict:
        """Mark an uploaded clip/image with shot-list ids from docs/FILMLISTA.md (e.g. ["fa-m1"], ["gk-o1"]) so
        recipes find it (plan_cut_from_recipe). Replaces the file's previous shot ids, keeps its other tags, adds the
        role footage. Unknown ids are rejected. description: what is visible (optional; default the shot text).
        An empty list removes the shot ids."""
        from engine.ad_studio.service import serialize_tags

        company = company_for(company_ref)
        tags = safe_call(footage.set_tags, company, asset_id, footage_ids, description=description)
        shot_ids = footage.ids_of(tags.tags)
        return {"asset_id": str(tags.asset_id), "footage_ids": shot_ids,
                "shots": [{"id": i, "text": footage.text(i)} for i in shot_ids], "tags": serialize_tags(tags)}

    @mcp.tool(title="Render cut in the cloud", annotations=write)
    @database_tool
    def render_cut(company_ref: str, cut_spec: dict) -> dict:
        """Cut a finished video in the cloud (HyperFrames on GitHub Actions, free) from media already in the
        company's media bank. Prefer render_recipe / plan_cut_from_recipe, which build this spec from a recipe;
        use render_cut for hand-made or adjusted specs (e.g. the spec returned by plan_cut_from_recipe). When it is done it is stored in the media bank and posted to the company's Discord
        review channel automatically, unless the quality gate holds it back (AI score under 7 or more than half of
        the scene time still images). Prefer video clips over still images. Returns the job; poll with get_cut_job (rendering takes ~3–10 min).

        cut_spec (schema "cut/v1"):
        {"schema": "cut/v1", "format": "9:16"|"4:5"|"1:1"|"16:9", "fps": 30, "title": "…", "caption": "post text",
         "recipe_id": "<library recipe id or null>", "brand": "<company brand id, optional>",
         "scenes": [{"id": "s1", "purpose": "hook", "duration_s": 2.0, "asset_id": "<MediaAsset uuid, video or image>",
                     "trim_start_s": 0.0, "fit": "cover"|"contain", "text": "Kort *betonad* text",
                     "text_style": "<catalog text id or null>", "text_position": "top"|"center"|"bottom"|null,
                     "audio": "mute"|"keep"|null, "effects": ["<catalog effect/grade ids>"],
                     "transition_in": "<catalog transition id or null>"}],
         "music_asset_id": "<audio MediaAsset uuid or null>", "music_volume": 1.0,
         "cta": {"text": "Läs mer", "url": "https://…", "duration_s": 2.5} | null}
        Max 90 s in total including the end card. Words wrapped in *asterisks* get the brand accent color.
        Library ids come from search_content_library (catalog.json); ids the cut template does not support yet are
        skipped and listed in `warnings` (never an error). Max 3 active jobs per company."""
        company = company_for(company_ref)
        job = safe_call(service.create_job, company, cut_spec)
        return service.serialize(job)

    @mcp.tool(title="Get cut job", annotations=read)
    @database_tool
    def get_cut_job(company_ref: str, job_id: str) -> dict:
        """Status of a cloud cut job: queued → claimed → rendering → done/failed, with warnings, error,
        output_asset_id (master), preview_asset_id, review_id, the video link once it is posted for review, and
        ai_critique (score 1–10, hook, legibility, pacing, brand fit, top 3 fixes per scene/library id) when done,
        quality_gate ({"passed", "reasons"}: held back from Discord when passed=false; fix and render again, or
        send_cut_for_review on the user's request) and render (beats, sfx, typography, technical qa)."""
        company = company_for(company_ref)
        return service.serialize(safe_call(service.get_job, company, job_id))

    @mcp.tool(title="Send held-back cut for review", annotations=write)
    @database_tool
    def send_cut_for_review(company_ref: str, job_id: str) -> dict:
        """Post a finished cut that the quality gate held back (quality_gate.passed=false: AI score under 7 or mostly
        still images) to the Discord review anyway. Only on the user's explicit request; otherwise fix what
        quality_gate.reasons and ai_critique.fixes say and render again."""
        company = company_for(company_ref)
        return service.serialize(safe_call(service.send_anyway, company, job_id))
