"""Versioned public contracts. Unknown fields/operations never reach engine services."""
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

CONTRACT_VERSION = 1
Workflow = Literal["auto", "image", "video", "motion", "sequence", "text"]
Role = Literal["start", "end", "reference", "logo", "audio"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Attachment(Contract):
    asset_id: UUID
    role: Role = "reference"


class TurnRequest(Contract):
    key: UUID
    expected_revision: int = Field(ge=0)
    message: str = Field(min_length=1, max_length=6000)
    workflow: Workflow = "auto"
    model: str = Field(default="", max_length=120)
    shape: Literal["portrait", "square", "landscape"] = "portrait"
    priority: Literal["balanced", "economy", "quality"] = "balanced"
    image_policy: Literal["contain", "crop"] = "contain"
    max_cost_usd: Decimal = Field(default=Decimal("5.00"), ge=Decimal("0"), le=Decimal("1000"), max_digits=7, decimal_places=2)
    template: str = Field(default="", max_length=80)
    attachments: list[Attachment] = Field(default_factory=list, max_length=8)


class Question(Contract):
    text: str = Field(min_length=1, max_length=240)
    options: list[str] = Field(default_factory=list, max_length=3)


class Proposal(Contract):
    """Model proposes meaning and copy. It cannot choose file IDs or start tools."""
    answer: str = Field(min_length=1, max_length=1800)
    title: str = Field(min_length=1, max_length=160)
    workflow: Literal["image", "video", "motion", "sequence", "text"]
    brief: str = Field(min_length=1, max_length=6000)
    clip_brief: str = Field(default="", max_length=6000)
    clip_duration_seconds: int | None = Field(default=None, ge=1, le=120)
    headline: str = Field(default="", max_length=240)
    body: str = Field(default="", max_length=500)
    cta: str = Field(default="", max_length=100)
    caption: str = Field(default="", max_length=1800)
    audio: Literal["none", "music", "native"] = "none"
    questions: list[Question] = Field(default_factory=list, max_length=3)


class ActionRequest(Contract):
    plan_id: UUID
    expected_revision: int = Field(ge=1)
    action: Literal["prepare", "start", "compose", "preview", "approve_preview", "final", "cancel"]
    job_id: UUID | None = None


class TemplateRequest(Contract):
    title: str = Field(min_length=1, max_length=160)
    instructions: str = Field(min_length=1, max_length=4000)
    kind: Workflow = "auto"
    key: str = Field(default="", max_length=80, pattern=r"^[a-z0-9-]*$")
