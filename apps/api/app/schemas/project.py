from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    prompt: str = Field(min_length=5, max_length=4000)
    platform: str = "instagram_reel"
    language: str = "hi-IN"
    dialect: str = "hinglish"
    style: str = "business_funny"
    duration_seconds: int = Field(default=30, ge=5, le=600)
    aspect_ratio: str = "9:16"
    quality: str = "balanced"


class SceneUpdate(BaseModel):
    duration_seconds: float | None = Field(default=None, ge=2, le=30)
    dialogue: str | None = Field(default=None, max_length=5000)
    visual_prompt: str | None = Field(default=None, max_length=5000)
    generation_mode: str | None = Field(default=None, max_length=30)
    metadata_json: dict[str, Any] | None = None


class SceneRegenerateRequest(BaseModel):
    instruction: str = Field(default="Make this scene stronger and more engaging.", max_length=1000)


class MediaAssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    scene_id: str | None = None
    kind: str
    provider: str
    status: str
    url: str
    cost_credits: int
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class SceneRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    order_index: int
    duration_seconds: float
    dialogue: str
    visual_prompt: str
    generation_mode: str
    asset_url: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    media_assets: list[MediaAssetRead] = Field(default_factory=list)


class ArtifactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    kind: str
    url: str
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    prompt: str
    platform: str
    language: str
    dialect: str
    style: str
    duration_seconds: int
    aspect_ratio: str
    quality: str
    status: str
    estimated_credits: int
    created_at: datetime
    scenes: list[SceneRead] = Field(default_factory=list)
    artifacts: list[ArtifactRead] = Field(default_factory=list)
    media_assets: list[MediaAssetRead] = Field(default_factory=list)


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    status: str
    progress: int
    error: str | None = None


class EngineRenderRequest(BaseModel):
    mode: str = Field(default="preview", pattern="^(preview|full)$")
    quality: str = Field(default="draft", pattern="^(draft|standard|high)$")


class SceneMediaRequest(BaseModel):
    voice: str = Field(default="Lekha", max_length=80)
    speech_rate: int = Field(default=185, ge=100, le=260)
    force: bool = False


class ProjectMediaRequest(BaseModel):
    voice: str = Field(default="Lekha", max_length=80)
    speech_rate: int = Field(default=185, ge=100, le=260)
    force: bool = False


class ComposeRequest(BaseModel):
    burn_subtitles: bool = True
    resolution: str = Field(default="1080x1920", pattern=r"^\d{3,4}x\d{3,4}$")
