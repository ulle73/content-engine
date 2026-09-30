"""Export the same validated contract for the Node worker; run in CI to check drift."""

import json
from pathlib import Path
from engine.motion.schema import MotionSpec
from engine.motion.catalog import ids

root = Path(__file__).resolve().parents[1]
schema = MotionSpec.model_json_schema()
for field, kinds in [
    ("component", ("text", "data", "scene")),
    ("background", ("background",)),
    ("transition", ("transition",)),
]:
    schema["$defs"]["Scene"]["properties"][field]["enum"] = sorted(ids(*kinds))
schema["$defs"]["Scene"]["properties"]["effects"]["items"]["enum"] = sorted(ids("effect"))
schema["$defs"]["Cue"]["properties"]["kind"]["enum"] = sorted(ids("audio"))
schema["properties"]["template_id"]["enum"] = sorted(ids("template"))
schema["properties"]["brand_id"]["enum"] = ["golfkuponger", "workspace"]
(root / "motion-renderer/spec.schema.json").write_text(json.dumps(schema, indent=2) + "\n")
