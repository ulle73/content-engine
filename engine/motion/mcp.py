"""Motion tools call exactly the same services as the browser."""

from django.urls import reverse
from mcp.types import ToolAnnotations

from engine.mcp_db import database_tool
from engine.operator_common import serialize_asset

from . import service
from .catalog import catalog
from .planner import compile_template


def serialize_project(project):
    revision = project.revisions.get(number=project.current_revision)
    return {
        "project_id": str(project.pk),
        "run_id": str(project.run_id),
        "title": project.title,
        "revision": project.current_revision,
        "spec": revision.spec,
        "approved_preview_id": str(project.approved_preview_id) if project.approved_preview_id else None,
        "workspace_url": reverse(
            "engine:motion_workspace", kwargs={"workspace_id": project.company_id, "project_id": project.pk}
        ),
        "renders": [
            {
                "render_id": str(job.pk),
                "mode": job.mode,
                "status": job.generation.status,
                "progress": job.progress,
                "error": job.generation.error,
                "asset": serialize_asset(job.output_asset) if job.output_asset else None,
            }
            for job in revision.renders.select_related("generation", "output_asset").order_by("-created_at")[:20]
        ],
    }


def register(mcp, company_for, run_for, user_for, safe_call):
    read = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)
    write = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False)

    @mcp.tool(title="Browse motion templates", annotations=read)
    @database_tool
    def list_motion_templates(company_ref: str, query: str = "") -> list[dict]:
        """Registered templates; fields and assets are data, never executable code."""
        company_for(company_ref)
        from .planner import template_schema

        return [dict(item, fields=template_schema(item["id"])) for item in catalog(query=query, kind="template")]

    @mcp.tool(title="List motion projects", annotations=read)
    @database_tool
    def list_motion_projects(company_ref: str) -> list[dict]:
        company = company_for(company_ref)
        return [serialize_project(project) for project in company.motion_projects.order_by("-updated_at")[:40]]

    @mcp.tool(title="Create motion project", annotations=write)
    @database_tool
    def create_motion_project(
        company_ref: str,
        title: str,
        template_id: str,
        fields: dict,
        idempotency_key: str,
        aspect_ratio: str = "9:16",
        audio: bool = True,
        run_id: str = "",
    ) -> dict:
        """Prepare a project without rendering. Use explicit facts and company-owned asset IDs. Optionally attach to a local content draft."""
        company = company_for(company_ref)
        spec = safe_call(
            compile_template,
            template_id,
            fields,
            aspect_ratio=aspect_ratio,
            audio=audio,
            brand_id="golfkuponger" if company.name.casefold() == "golfkuponger" else "workspace",
        )
        run = run_for(company_ref, run_id) if run_id else None
        return serialize_project(
            safe_call(service.create_project, company, user_for(), title=title, spec=spec, key=idempotency_key, run=run)
        )

    @mcp.tool(title="Read motion project", annotations=read)
    @database_tool
    def get_motion_project(company_ref: str, project_id: str) -> dict:
        return serialize_project(safe_call(service.get_project, company_for(company_ref), project_id))

    @mcp.tool(title="Update motion project", annotations=write)
    @database_tool
    def update_motion_project(
        company_ref: str, project_id: str, spec: dict, expected_revision: int, idempotency_key: str
    ) -> dict:
        """Create an immutable revision. Invalidates preview approval; rejects stale revisions and arbitrary code/URLs."""
        return serialize_project(
            safe_call(
                service.update_project,
                company_for(company_ref),
                user_for(),
                project_id,
                spec=spec,
                expected_revision=expected_revision,
                key=idempotency_key,
            )
        )

    @mcp.tool(title="Render motion project", annotations=write)
    @database_tool
    def render_motion_project(
        company_ref: str, project_id: str, mode: str, expected_revision: int, idempotency_key: str
    ) -> dict:
        """Queue preview or final rendering. Final requires an explicitly approved preview of the same revision. Read project status to poll."""
        job = safe_call(
            service.queue_render,
            company_for(company_ref),
            user_for(),
            project_id,
            mode=mode,
            expected_revision=expected_revision,
            key=idempotency_key,
        )
        return {"render_id": str(job.pk), "status": job.generation.status}

    @mcp.tool(title="Approve motion preview", annotations=write)
    @database_tool
    def approve_motion_preview(company_ref: str, project_id: str, render_id: str, expected_revision: int) -> dict:
        """Only approve after the user has reviewed the complete video and storyboard."""
        return serialize_project(
            safe_call(
                service.approve_preview,
                company_for(company_ref),
                user_for(),
                project_id,
                render_id=render_id,
                expected_revision=expected_revision,
            )
        )

    @mcp.tool(title="Cancel motion render", annotations=write)
    @database_tool
    def cancel_motion_render(company_ref: str, render_id: str) -> dict:
        job = safe_call(service.cancel_render, company_for(company_ref), render_id)
        return {"render_id": str(job.pk), "status": job.generation.status}
