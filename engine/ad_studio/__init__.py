"""Ad Studio: idea conversation -> locked AdBrief -> production.

brief.py    pure contract (AdBrief), no Django
models.py   AdDraft (persisted brief) and AssetTags (searchable image bank)
service.py  company-scoped operations used by MCP and future web UI
blueprints  Remotion template -> scene skeleton, and locked brief -> template fields
skills.py   read-only access to skills/<name>/SKILL.md
mcp.py      MCP tools
"""
