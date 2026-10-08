# content-engine Motion Engine (Remotion)

**Vad:** content-engines egen, versionerade motionkatalog – 107 poster ur `engine/motion/catalog.json`:
mallar (inkl. annonsmallarna i `engine/motion/ad_templates.py`), scener, datascener, textanimationer,
övergångar, bakgrunder, effekter och syntetiserade ljud. Renderas av `motion-renderer/` (Remotion).
**Licens:** repots egen kod. Remotion kräver licens enligt `MOTION_LICENSE_MODE` (se `docs/motion/USAGE.md`).
**Hur vi använder det:** via Motion Engine – webbappen (Media → Motion, eller ett utkast → Skapa
motionvideo) eller MCP (`list_motion_templates`, `create_motion_project`, `update_motion_project`,
`render_motion_project`, `approve_motion_preview`). Komponenter används i en MotionSpec
(`engine/motion/schema.py`): scenens `component`, `background`, `transition`, `effects` och `sfx`.
`path` pekar på renderarens källfil (komponenter) eller mallens definition (planner.py / ad_templates.py).
Källfilerna ändras inte härifrån; posterna är `unverified` tills en förhandsvisning renderats.
**Lokal sökväg:** `engine/motion/`, `motion-renderer/src/`.
