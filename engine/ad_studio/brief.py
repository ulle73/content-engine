"""AdBrief: the contract between the idea conversation and production.

The conversation is free. Production is not. Everything the user and the
assistant agree on during the idea phase ends up in one AdBrief. When the user
says "kör", the brief is locked: validated, frozen and hashed. Renderers
(Remotion/Motion, Higgsfield, Postiz delivery) only ever read a locked brief and
must not add, invent or "improve" anything that is not in it.

Phases (the assistant fills the brief progressively):
    1. goal      - message, objective, audience, offer
    2. angle     - chosen idea + hook
    3. assets    - chosen images/videos from the library or fresh uploads
    4. engine    - remotion (free) / higgsfield (paid) / hybrid
    5. story     - scene by scene
    6. lock      - lock() -> immutable, hashed, ready for production

This module is pure (no Django) so it can be used by MCP tools, the web UI and
tests alike. Existing CreativeBrief/MotionSpec stay as the per-engine compile
targets; AdBrief sits above them.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

AD_BRIEF_VERSION = "ad-brief/1"

# Hard copy rules. These are craft rules for short social video, not taste.
MAX_WORDS_ON_SCREEN = 8          # per scene; people read ~3-4 words/second
MIN_SCENE_SECONDS = 1.0
DURATION_TOLERANCE_SECONDS = 0.25

Format = Literal["9:16", "4:5", "1:1", "16:9"]
Engine = Literal["remotion", "higgsfield", "hybrid"]
Objective = Literal["awareness", "consideration", "conversion", "retargeting"]
AssetRole = Literal["hook", "footage", "screen", "product", "proof", "end_card", "logo", "other"]
ScenePurpose = Literal["hook", "problem", "solution", "how", "proof", "offer", "cta"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Fact(_Strict):
    """A claim shown or said in the ad. Must come from an approved source."""

    claim: str = Field(min_length=1, max_length=300)
    source: str = Field(min_length=1, max_length=300, description="Skill section, URL or document the claim comes from")
    verified: bool = False


class Asset(_Strict):
    asset_id: str = Field(min_length=1, max_length=100)
    role: AssetRole
    origin: Literal["library", "upload", "generate"] = "library"
    note: str = Field(default="", max_length=300)
    # Only for origin == "generate": what Higgsfield/an image model should make.
    generation_prompt: str = Field(default="", max_length=2000)


class Scene(_Strict):
    id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,39}$")
    purpose: ScenePurpose
    duration_s: float = Field(ge=MIN_SCENE_SECONDS, le=30)
    asset_id: str | None = None
    on_screen_text: str = Field(default="", max_length=120)
    voiceover: str = Field(default="", max_length=300)
    motion: str = Field(default="", max_length=200, description="Camera/animation intent in plain words")
    transition_in: Literal["cut", "fade", "slide", "zoom", "whip"] = "cut"


class AdCopy(_Strict):
    """Text around the video in the feed (Meta primary text / headline)."""

    primary_text: str = Field(default="", max_length=600)
    headline: str = Field(default="", max_length=60)
    cta_label: str = Field(default="Läs mer", max_length=30)
    landing_url: str = Field(default="https://golfkuponger.se", max_length=300)


class Angle(_Strict):
    title: str = Field(min_length=1, max_length=120)
    hook: str = Field(min_length=1, max_length=120)
    why_it_works: str = Field(default="", max_length=400)


class EngineChoice(_Strict):
    engine: Engine
    remotion_template_id: str | None = None
    estimated_cost_sek: float = Field(default=0, ge=0)
    cost_approved: bool = False


class AdBrief(_Strict):
    version: str = AD_BRIEF_VERSION
    company: str = "golfkuponger"
    brand_preset: str = "golfkuponger"

    # Phase 1 - goal
    message: str = Field(default="", max_length=200, description="The one thing the viewer should remember")
    objective: Objective | None = None
    audience: str = Field(default="", max_length=300)
    offer: str = Field(default="", max_length=200)
    campaign: str = Field(default="", max_length=100)

    # Phase 2 - angle
    angle: Angle | None = None

    # Phase 3 - assets
    assets: list[Asset] = Field(default_factory=list)

    # Phase 4 - engine
    engine: EngineChoice | None = None

    # Phase 5 - story
    formats: list[Format] = Field(default_factory=lambda: ["9:16"])
    duration_s: float | None = Field(default=None, ge=3, le=60)
    scenes: list[Scene] = Field(default_factory=list)
    copy_: AdCopy = Field(default_factory=AdCopy, alias="copy")
    facts: list[Fact] = Field(default_factory=list)
    forbid: list[str] = Field(default_factory=list, description="Explicit don'ts agreed in the conversation")
    variants: int = Field(default=1, ge=1, le=3)

    # Phase 6 - lock
    status: Literal["draft", "locked"] = "draft"
    locked_at: str | None = None
    lock_hash: str | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, populate_by_name=True)

    # ---- progress -----------------------------------------------------

    def missing(self) -> list[str]:
        """What still has to be decided before lock. Drives the next question."""
        gaps = []
        if not self.message:
            gaps.append("message")
        if not self.objective:
            gaps.append("objective")
        if not self.audience:
            gaps.append("audience")
        if not self.angle:
            gaps.append("angle")
        if not self.assets:
            gaps.append("assets")
        if not self.engine:
            gaps.append("engine")
        if not self.scenes:
            gaps.append("scenes")
        if self.duration_s is None:
            gaps.append("duration_s")
        if not self.copy_.headline:
            gaps.append("copy.headline")
        return gaps

    def problems(self) -> list[str]:
        """Rule violations. Empty list == lockable (together with missing())."""
        out = []
        asset_ids = {a.asset_id for a in self.assets}

        ids = [s.id for s in self.scenes]
        if len(ids) != len(set(ids)):
            out.append("Scen-id måste vara unika.")

        for s in self.scenes:
            words = len(s.on_screen_text.split())
            if words > MAX_WORDS_ON_SCREEN:
                out.append(f"Scen '{s.id}': {words} ord på skärmen, max {MAX_WORDS_ON_SCREEN}.")
            if s.asset_id and s.asset_id not in asset_ids:
                out.append(f"Scen '{s.id}' använder asset '{s.asset_id}' som inte är vald.")

        if self.scenes:
            if self.scenes[0].purpose != "hook":
                out.append("Första scenen måste vara en hook.")
            if self.scenes[-1].purpose != "cta":
                out.append("Sista scenen måste vara en CTA.")
            total = sum(s.duration_s for s in self.scenes)
            if self.duration_s is not None and abs(total - self.duration_s) > DURATION_TOLERANCE_SECONDS:
                out.append(f"Scenerna är {total:g} s men annonsen ska vara {self.duration_s:g} s.")

        if self.engine:
            if self.engine.engine in ("higgsfield", "hybrid") and not self.engine.cost_approved:
                out.append("Higgsfield kostar pengar: kostnaden måste godkännas innan låsning.")
            if self.engine.engine in ("remotion", "hybrid") and not self.engine.remotion_template_id:
                out.append("Remotion kräver en vald mall (remotion_template_id).")
        if any(a.origin == "generate" for a in self.assets):
            if not self.engine or self.engine.engine == "remotion":
                out.append("Assets som ska genereras kräver Higgsfield eller hybrid.")
            for a in self.assets:
                if a.origin == "generate" and not a.generation_prompt:
                    out.append(f"Asset '{a.asset_id}' ska genereras men saknar generation_prompt.")

        unverified = [f.claim for f in self.facts if not f.verified]
        if unverified:
            out.append("Overifierade påståenden: " + "; ".join(unverified))
        return out

    # ---- lock ---------------------------------------------------------

    def canonical_json(self) -> str:
        data = self.model_dump(mode="json", by_alias=True, exclude={"status", "locked_at", "lock_hash"})
        return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def lock(self) -> "AdBrief":
        """Return a locked, hashed copy. Raises BriefNotReady with reasons."""
        if self.status == "locked":
            return self
        reasons = [f"Saknas: {m}" for m in self.missing()] + self.problems()
        if reasons:
            raise BriefNotReady(reasons)
        digest = hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()
        return self.model_copy(
            update={
                "status": "locked",
                "locked_at": datetime.now(timezone.utc).isoformat(),
                "lock_hash": digest,
            }
        )

    def verify_lock(self) -> bool:
        """Production calls this first. A tampered brief must not render."""
        if self.status != "locked" or not self.lock_hash:
            return False
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest() == self.lock_hash

    @model_validator(mode="after")
    def _locked_must_have_hash(self):
        if self.status == "locked" and not self.lock_hash:
            raise ValueError("A locked brief must carry lock_hash; use lock().")
        return self


class BriefNotReady(ValueError):
    def __init__(self, reasons: list[str]):
        self.reasons = reasons
        super().__init__("Briefen kan inte låsas än:\n- " + "\n- ".join(reasons))


def json_schema() -> dict:
    """Schema for MCP tool input/output and the web UI."""
    return AdBrief.model_json_schema(by_alias=True)
