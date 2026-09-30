"""Closed, URL-free MotionSpec. Rendering accepts data, never user code."""

from __future__ import annotations
import hashlib
import json
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator
from .catalog import get_item

Number = Annotated[float, Field(strict=True, allow_inf_nan=False, ge=-1e12, le=1e12)]
Slug = Annotated[str, Field(pattern=r"^[a-z][a-z0-9-]{0,63}$")]


class Closed(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_default=True)


class Item(Closed):
    label: str = Field(max_length=100)
    value: Number = 0


class Props(Closed):
    headline: str = Field(default="", max_length=240)
    eyebrow: str = Field(default="", max_length=80)
    body: str = Field(default="", max_length=500)
    value: Number = 0
    unit: str = Field(default="", max_length=16)
    items: list[Item] = Field(default_factory=list, max_length=12)
    asset_id: UUID | None = None
    secondary_asset_id: UUID | None = None
    cta: str = Field(default="", max_length=100)
    attribution: str = Field(default="", max_length=160)
    alignment: Literal["left", "center"] = "left"


class Cue(Closed):
    kind: Slug
    frame: StrictInt = Field(ge=0, le=7200)
    gain: float = Field(default=0.4, ge=0, le=1, strict=True, allow_inf_nan=False)

    @field_validator("kind")
    @classmethod
    def registered(cls, value):
        get_item(value, kinds={"audio"})
        return value


class Scene(Closed):
    id: Slug
    component: Slug
    duration_frames: StrictInt = Field(ge=12, le=1800)
    props: Props = Field(default_factory=Props)
    background: Slug = "solid"
    transition: Slug = "cut"
    transition_frames: StrictInt = Field(default=0, ge=0, le=60)
    effects: list[Slug] = Field(default_factory=list, max_length=3)
    sfx: list[Cue] = Field(default_factory=list, max_length=40)

    @model_validator(mode="after")
    def registered_and_bounded(self):
        get_item(self.component, kinds={"text", "data", "scene"})
        get_item(self.background, kinds={"background"})
        get_item(self.transition, kinds={"transition"})
        for effect in self.effects:
            get_item(effect, kinds={"effect"})
        if len(set(self.effects)) != len(self.effects):
            raise ValueError("Duplicate effects")
        if self.transition == "cut" and self.transition_frames != 0:
            raise ValueError("Cut transition must have zero frames")
        if self.transition != "cut" and not 1 <= self.transition_frames < self.duration_frames // 2:
            raise ValueError("Transition must be shorter than half the scene")
        if any(cue.frame >= self.duration_frames for cue in self.sfx):
            raise ValueError("Sound cue lies outside scene")
        if self.component in {"bars", "donut", "percentage"} and (
            self.props.value < 0 or any(item.value < 0 for item in self.props.items)
        ):
            raise ValueError("This visualization requires non-negative values")
        if self.component == "percentage" and self.props.value > 100:
            raise ValueError("Percentage must be within 0..100")
        return self


class Audio(Closed):
    enabled: bool = True
    gain: float = Field(default=0.7, ge=0, le=1, strict=True, allow_inf_nan=False)
    music: Literal["none", "bed", "pulse"] = "bed"
    music_asset_id: UUID | None = None
    fade_frames: StrictInt = Field(default=15, ge=0, le=120)
    ducking: float = Field(default=0.3, ge=0, le=1, strict=True, allow_inf_nan=False)


class MotionSpec(Closed):
    version: Literal[1] = 1
    template_id: Slug
    template_version: StrictInt = 1
    aspect_ratio: Literal["9:16", "1:1", "16:9"] = "9:16"
    fps: Literal[24, 25, 30, 60] = 30
    seed: StrictInt = Field(default=42, ge=0, le=2147483647)
    brand_id: Slug = "golfkuponger"
    scenes: list[Scene] = Field(min_length=1, max_length=24)
    audio: Audio = Field(default_factory=Audio)
    end_card_asset_id: UUID | None = None

    @field_validator("fps", "version", mode="before")
    @classmethod
    def literal_integer(cls, value):
        if type(value) is not int:
            raise ValueError("Integer required")
        return value

    @model_validator(mode="after")
    def coherent_timeline(self):
        get_item(self.template_id, kinds={"template"}, version=self.template_version)
        if len({scene.id for scene in self.scenes}) != len(self.scenes):
            raise ValueError("Scene IDs must be unique")
        if self.scenes[0].transition_frames or self.scenes[0].transition != "cut":
            raise ValueError("First scene must start with a cut")
        if sum(s.duration_frames - s.transition_frames for s in self.scenes) > 120 * self.fps:
            raise ValueError("Video cannot exceed 120 seconds")
        for index, scene in enumerate(self.scenes):
            if index and scene.transition_frames >= self.scenes[index - 1].duration_frames // 2:
                raise ValueError("Transition consumes previous scene")
            ticks = sorted(c.frame for c in scene.sfx if c.kind == "tick")
            if any(b - a < self.fps / 6 for a, b in zip(ticks, ticks[1:])):
                raise ValueError("Counter ticks are limited to six per second")
        return self


def validate_spec(value: dict) -> dict:
    if not isinstance(value, dict):
        raise ValueError("MotionSpec must be an object")
    if len(json.dumps(value, allow_nan=False).encode()) > 150_000:
        raise ValueError("MotionSpec is too large")
    return MotionSpec.model_validate(value).model_dump(mode="json")


def spec_hash(value: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            validate_spec(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode()
    ).hexdigest()


def timeline(value: dict) -> list[dict]:
    result = []
    end = 0
    for scene in value["scenes"]:
        start = end - scene["transition_frames"]
        end = start + scene["duration_frames"]
        result.append({"id": scene["id"], "start": start, "end": end})
    return result


def asset_ids(value: dict) -> set[str]:
    result = {str(value[k]) for k in ("end_card_asset_id",) if value.get(k)}
    if value["audio"].get("music_asset_id"):
        result.add(str(value["audio"]["music_asset_id"]))
    for scene in value["scenes"]:
        for key in ("asset_id", "secondary_asset_id"):
            if scene["props"].get(key):
                result.add(str(scene["props"][key]))
    return result
