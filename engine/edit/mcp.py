"""MCP tools for cloud editing: send a cut spec to the HyperFrames renderer on GitHub Actions and follow the job."""

from mcp.types import ToolAnnotations

from engine.mcp_db import database_tool

from . import service


def register(mcp, company_for, safe_call):
    read = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)
    write = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True)

    @mcp.tool(title="Render cut in the cloud", annotations=write)
    @database_tool
    def render_cut(company_ref: str, cut_spec: dict) -> dict:
        """Cut a finished video in the cloud (HyperFrames on GitHub Actions, free) from media already in the
        company's media bank. When it is done it is stored in the media bank and posted to the company's Discord
        review channel automatically. Returns the job; poll with get_cut_job (rendering takes ~3–10 min).

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
        output_asset_id (master), preview_asset_id, review_id and the video link once it is posted for review."""
        company = company_for(company_ref)
        return service.serialize(safe_call(service.get_job, company, job_id))
