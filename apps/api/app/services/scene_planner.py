from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.core.config import get_settings
from app.services.llm import LLMError, chat_json


@dataclass(slots=True)
class PlannedScene:
    order_index: int
    duration_seconds: float
    dialogue: str
    visual_prompt: str
    generation_mode: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PlannedStory:
    title: str
    hook: str
    running_joke: str
    twist: str
    characters: list[str]
    scenes: list[PlannedScene]
    provider: str
    model: str
    fallback_used: bool = False
    fallback_reason: str | None = None


class DialogueTurn(BaseModel):
    speaker: str = Field(min_length=1, max_length=50)
    text: str = Field(min_length=1, max_length=500)
    emotion: str = "neutral"
    pose: str = "idle"


class LLMScene(BaseModel):
    duration_seconds: float = Field(ge=2, le=20)
    setup: str = ""
    dialogue: list[DialogueTurn] = Field(default_factory=list)
    visual_prompt: str = Field(min_length=5, max_length=1200)
    generation_mode: str = "BLENDER_3D"
    camera: str = "speaker_medium"
    visual_action: str = "dialogue"
    props: list[str] = Field(default_factory=list)
    visual_characters: list[str] = Field(default_factory=list)
    blocking: list[dict[str, Any]] = Field(default_factory=list)
    expression_beats: list[dict[str, Any]] = Field(default_factory=list)


class LLMStory(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    hook: str = ""
    running_joke: str = ""
    twist: str = ""
    characters: list[str] = Field(default_factory=list)
    scenes: list[LLMScene] = Field(min_length=3, max_length=40)


def _scene_count(duration_seconds: int) -> int:
    # Reels/Shorts need rapid 5-7s beats; long-form cartoons use ~13.3s shots.
    if duration_seconds <= 90:
        return max(3, min(15, math.ceil(duration_seconds / 6)))
    return max(8, min(36, math.ceil(duration_seconds / 13.33)))


def _dialect_contract(language: str, dialect: str) -> str:
    if dialect.lower() == "kanpuriya":
        return (
            "Use natural, understandable Kanpuriya Hindi grammar and rhythm throughout, not standard Hindi "
            "with a few slang words. Prefer forms like 'का बे', 'हम बताय दे रहे हैं', 'काहे', 'करत हो', "
            "and situation-appropriate Kanpuriya punchlines. Keep it family-safe and widely understandable."
        )
    if dialect.lower() == "hinglish":
        return "Use natural urban Indian Hinglish, concise spoken lines, not formal translated Hindi."
    return f"Write natural spoken dialogue for language={language}, dialect={dialect}."


def _system_prompt() -> str:
    return """You are the story and scene-planning engine for BharatVideo AI.
Return ONLY valid JSON. Never use markdown fences.
Make the video immediately engaging, visually producible, and concise.
Each scene must advance the story. Avoid filler and dead air.
For comedy, create escalating misunderstandings, physical actions and a final twist.
The output schema is:
{
  "title": "...",
  "hook": "...",
  "running_joke": "...",
  "twist": "...",
  "characters": ["..."],
  "scenes": [
    {
      "duration_seconds": 6,
      "setup": "what physically happens",
      "dialogue": [{"speaker":"name","text":"line","emotion":"shocked","pose":"pointing"}],
      "visual_prompt": "visual description",
      "generation_mode": "BLENDER_3D",
      "camera": "speaker_medium",
      "visual_action": "point_phone",
      "props": ["phone"],
      "visual_characters": ["babuji","guddu","bittu"],
      "blocking": [{"character":"babuji","action":"recoil","strength":1.0}],
      "expression_beats": [{"character":"babuji","emotion":"shock","at":0.25}]
    }
  ]
}
Allowed generation_mode values: BLENDER_3D, AI_VIDEO, AI_IMAGE, TEMPLATE.
For low-cost MVP planning, prefer BLENDER_3D or TEMPLATE unless an AI cinematic shot is clearly valuable.
For Kanpuri comedy, Babuji, Guddu and Bittu are the locked recurring cast. Keep all three visually present in most scenes, even when only one speaks. Every scene needs a visible physical action: approach, recoil, sit, stand, whisper lean, phone handoff, prop grab, point, chase step, or reaction turn. Avoid three characters simply standing in a line. Scene 1 must visually explain the story hook before dialogue alone is needed. Use story-specific props and reaction close-ups.
"""


def _mock_story(prompt: str, duration_seconds: int, language: str, dialect: str) -> PlannedStory:
    count = _scene_count(duration_seconds)
    per_scene = duration_seconds / count
    scenes: list[PlannedScene] = []
    for i in range(count):
        text = f"Scene {i + 1}: {prompt[:110]}"
        scenes.append(
            PlannedScene(
                order_index=i,
                duration_seconds=round(per_scene, 2),
                dialogue=text,
                visual_prompt=f"{prompt}. Beat {i + 1}. Language={language}; dialect={dialect}.",
                generation_mode="BLENDER_3D",
                metadata={
                    "setup": f"Deterministic 3D fallback beat {i + 1}",
                    "camera": "reaction_close" if i % 2 else "speaker_medium",
                    "visual_action": ["mock_shock","snatch_phone","whisper","phone_pass"][i % 4],
                    "props": ["ai_phone"] if ("ai" in prompt.lower() or "phone" in prompt.lower()) else ["chai_glass"],
                    "visual_characters": ["babuji", "guddu", "bittu"],
                    "blocking": [{"character":"babuji","action":"recoil_or_point","strength":1.0},{"character":"guddu","action":"approach","strength":0.8},{"character":"bittu","action":"listener_reaction","strength":0.9}],
                    "expression_beats": [{"character":"babuji","emotion":"shock","at":0.25},{"character":"guddu","emotion":"worried","at":0.5},{"character":"bittu","emotion":"smug","at":0.7}],
                    "cast_lock": "babuji_guddu_bittu",
                    "lip_sync_mode": "viseme_ready_v07",
                    "dialogue_turns": [{"speaker": ["babuji","guddu","bittu"][i % 3], "text": text, "emotion": "shocked" if i == 0 else "comic", "pose": "pointing" if i % 2 == 0 else "reacting"}],
                },
            )
        )
    return PlannedStory(
        title=prompt[:80] or "BharatVideo Project",
        hook="Fast opening hook",
        running_joke="",
        twist="",
        characters=["babuji", "guddu", "bittu"],
        scenes=scenes,
        provider="mock",
        model="deterministic-v0.2",
        fallback_used=True,
    )


def _performance_metadata(*, idx: int, prompt: str, style: str, scene: LLMScene, turns: list[dict[str, Any]]) -> dict[str, Any]:
    comedy = "kanpuri" in style.lower() or "comedy" in style.lower()
    if not comedy:
        return {
            "visual_characters": scene.visual_characters,
            "blocking": scene.blocking,
            "expression_beats": scene.expression_beats,
        }
    actions = ["mock_shock", "snatch_phone", "whisper", "phone_pass", "ai_interview", "backpedal", "offer_sweets"]
    camera = ["speaker_close_up", "speaker_close_up", "speaker_medium", "speaker_medium", "speaker_close_up", "speaker_medium"]
    props = list(scene.props)
    lower = f"{prompt} {scene.visual_prompt} {scene.setup}".lower()
    if "ai" in lower or "phone" in lower or "mobile" in lower:
        if "ai_phone" not in props: props.insert(0, "ai_phone")
    if not props:
        props = ["chai_glass" if idx % 2 else "charpai"]
    visual_characters = ["babuji", "guddu", "bittu"]
    blocking = scene.blocking or [
        {"character": "babuji", "action": actions[idx % len(actions)], "strength": 1.0},
        {"character": "guddu", "action": "approach_or_recoil", "strength": 0.8},
        {"character": "bittu", "action": "listener_reaction_or_whisper", "strength": 0.9},
    ]
    expressions = scene.expression_beats or [
        {"character": "babuji", "emotion": "shock" if idx == 0 else ("angry" if idx % 3 == 0 else "confused"), "at": 0.22},
        {"character": "guddu", "emotion": "worried", "at": 0.46},
        {"character": "bittu", "emotion": "smug" if idx % 2 else "shock", "at": 0.66},
    ]
    return {
        "visual_characters": visual_characters,
        "blocking": blocking,
        "expression_beats": expressions,
        "camera_override": camera[idx % len(camera)],
        "visual_action_override": actions[idx % len(actions)],
        "props_override": props,
        "cast_lock": "babuji_guddu_bittu",
        "lip_sync_mode": "viseme_ready_v07",
        "story_prop_required": True,
    }


def plan_story(prompt: str, duration_seconds: int, language: str, dialect: str, style: str) -> PlannedStory:
    settings = get_settings()
    if settings.llm_provider.lower() == "mock":
        return _mock_story(prompt, duration_seconds, language, dialect)

    count = _scene_count(duration_seconds)
    user_prompt = f"""Create a video plan.
User idea: {prompt}
Target total duration: {duration_seconds} seconds
Target number of scenes: exactly {count}
Language: {language}
Dialect: {dialect}
Style: {style}
Platform pacing: hook in scene 1, strong pattern interrupt every 2-3 scenes, twist/payoff at the end.
{_dialect_contract(language, dialect)}
Keep the SUM of scene duration_seconds close to {duration_seconds} seconds.
"""
    try:
        result = chat_json(_system_prompt(), user_prompt)
        story = LLMStory.model_validate(result.data)
        if len(story.scenes) != count:
            # Accept close model output, but normalize total duration below.
            if not 3 <= len(story.scenes) <= 40:
                raise LLMError(f"LLM returned unusable scene count: {len(story.scenes)}")

        raw_total = sum(scene.duration_seconds for scene in story.scenes) or 1.0
        scale = duration_seconds / raw_total
        planned: list[PlannedScene] = []
        for idx, scene in enumerate(story.scenes):
            turns = [turn.model_dump() for turn in scene.dialogue]
            dialogue = "\n".join(f"{turn.speaker}: {turn.text}" for turn in scene.dialogue).strip()
            perf = _performance_metadata(idx=idx, prompt=prompt, style=style, scene=scene, turns=turns)
            planned.append(
                PlannedScene(
                    order_index=idx,
                    duration_seconds=round(max(2.0, scene.duration_seconds * scale), 2),
                    dialogue=dialogue,
                    visual_prompt=scene.visual_prompt,
                    generation_mode=("BLENDER_3D" if ("kanpuri" in style.lower() or "comedy" in style.lower()) else scene.generation_mode.upper()),
                    metadata={
                        "setup": scene.setup,
                        "camera": perf.get("camera_override") or scene.camera,
                        "visual_action": perf.get("visual_action_override") or scene.visual_action,
                        "props": perf.get("props_override") or scene.props,
                        "dialogue_turns": turns,
                        "story_hook": story.hook,
                        "running_joke": story.running_joke,
                        "twist": story.twist,
                        **{k:v for k,v in perf.items() if not k.endswith("_override")},
                    },
                )
            )
        return PlannedStory(
            title=story.title,
            hook=story.hook,
            running_joke=story.running_joke,
            twist=story.twist,
            characters=story.characters,
            scenes=planned,
            provider=result.provider,
            model=result.model,
        )
    except (LLMError, ValidationError, ValueError, json.JSONDecodeError) as exc:
        if not settings.llm_fallback_to_mock:
            raise
        fallback = _mock_story(prompt, duration_seconds, language, dialect)
        fallback.fallback_reason = str(exc)
        return fallback


def regenerate_scene_content(
    *, prompt: str, language: str, dialect: str, style: str, current_scene: dict[str, Any], instruction: str
) -> PlannedScene:
    settings = get_settings()
    if settings.llm_provider.lower() == "mock":
        updated = PlannedScene(**current_scene)
        updated.dialogue = f"{updated.dialogue}\n[Mock rewrite] {instruction}".strip()
        return updated

    schema = """Return ONLY JSON with keys: duration_seconds, setup, dialogue, visual_prompt,
generation_mode, camera, visual_action, props. dialogue is an array of objects with speaker,text,emotion,pose."""
    user = f"""Rewrite ONE scene while preserving story continuity.
Overall project: {prompt}
Language={language}; dialect={dialect}; style={style}
{_dialect_contract(language, dialect)}
Instruction: {instruction or 'Make this scene stronger and more engaging.'}
Current scene JSON: {json.dumps(current_scene, ensure_ascii=False)}
{schema}
"""
    result = chat_json("You rewrite exactly one video scene. Return only the requested JSON object and no markdown.", user)
    scene = LLMScene.model_validate(result.data)
    turns = [turn.model_dump() for turn in scene.dialogue]
    return PlannedScene(
        order_index=int(current_scene["order_index"]),
        duration_seconds=scene.duration_seconds,
        dialogue="\n".join(f"{x.speaker}: {x.text}" for x in scene.dialogue),
        visual_prompt=scene.visual_prompt,
        generation_mode=scene.generation_mode.upper(),
        metadata={
            "setup": scene.setup,
            "camera": scene.camera,
            "visual_action": scene.visual_action,
            "props": scene.props,
            "dialogue_turns": turns,
            "visual_characters": scene.visual_characters,
            "blocking": scene.blocking,
            "expression_beats": scene.expression_beats,
            "regenerated_by": result.provider,
            "regenerated_model": result.model,
        },
    )
