"""ChatGPT/Claude MCP entrypoints for the same technique bank used by Ad Studio."""

from mcp.types import ToolAnnotations
from engine.mcp_db import database_tool
from . import service


def register(mcp, company_for, user_for, safe_call):
    paid = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True)
    read = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)
    write = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False)

    @mcp.tool(
        title="Suggest techniques from a link",
        annotations=paid,
        description=(
            "When the user wants to add filmmaking, camera, hook or editing techniques from a URL, "
            "use this first. Safely read a public HTTPS article or reuse the existing reference-video "
            "analysis; a bounded OpenRouter text request proposes individual techniques and flags "
            "duplicates. Small AI analysis cost may apply; NEVER saves techniques yet, starts no video "
            "generation and does not copy the source footage to the Content Library. Show the "
            "numbered proposals to the user and obtain explicit approval before calling approve_techniques."
        ),
    )
    @database_tool
    def suggest_techniques_from_link(company_ref: str, url: str) -> dict:
        batch = safe_call(service.propose, company_for(company_ref), user_for(), url)
        return service.serialize(batch)

    @mcp.tool(title="Get technique suggestions", annotations=read)
    @database_tool
    def get_technique_suggestions(company_ref: str, import_id: str) -> dict:
        return service.serialize(safe_call(service.owned, company_for(company_ref), import_id))

    @mcp.tool(
        title="Approve selected techniques",
        annotations=write,
        description=(
            "Only after explicit operator approval: save selected 0-based suggestion indexes into "
            "the existing Content Library as company-owned searchable techniques. Requires confirmed=true; "
            "skips known duplicates and is idempotent. Never infer approval from merely posting a URL."
        ),
    )
    @database_tool
    def approve_techniques(company_ref: str, import_id: str, selected_indices: list[int],
                           confirmed: bool = False) -> dict:
        if confirmed is not True:
            raise ValueError("Be användaren godkänna de markerade teknikerna först.")
        return safe_call(service.approve, company_for(company_ref), user_for(), import_id, selected_indices)
