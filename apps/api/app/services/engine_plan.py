from __future__ import annotations

from typing import Any


BLENDER_ACTORS = ("babuji", "guddu", "bittu")


def _slug_character(value: str) -> str:
    value = value.strip().lower().replace(" ", "_")
    return value or "narrator"


def _speaker_alias(value: str) -> str:
    value = _slug_character(value)
    aliases = {
        "babu": "babuji", "babu_ji": "babuji", "father": "babuji", "dad": "babuji",
        "guddua": "guddu", "guddu_bhaiya": "guddu",
        "bittua": "bittu", "bittu_bhaiya": "bittu",
    }
    return aliases.get(value, value)


def _map_speakers_for_blender(scenes) -> dict[str, str]:
    """Map free-form LLM speaker names onto the renderer's stable actor rig IDs.

    Existing babuji/guddu/bittu names are preserved. Unknown non-narrator names are
    assigned deterministically in first-seen order. This adapter is only for the
    Blender cartoon renderer; the project's original scene metadata remains unchanged.
    """
    mapping: dict[str, str] = {}
    used = set()

    # Preserve known actors first.
    for scene in sorted(scenes, key=lambda x: x.order_index):
        for turn in ((scene.metadata_json or {}).get("dialogue_turns") or []):
            raw = _speaker_alias(str(turn.get("speaker") or "narrator"))
            if raw in BLENDER_ACTORS:
                mapping[raw] = raw
                used.add(raw)

    available = [actor for actor in BLENDER_ACTORS if actor not in used]
    cycle_index = 0
    for scene in sorted(scenes, key=lambda x: x.order_index):
        for turn in ((scene.metadata_json or {}).get("dialogue_turns") or []):
            raw = _speaker_alias(str(turn.get("speaker") or "narrator"))
            if raw == "narrator" or raw in mapping:
                continue
            if available:
                actor = available.pop(0)
            else:
                actor = BLENDER_ACTORS[cycle_index % len(BLENDER_ACTORS)]
                cycle_index += 1
            mapping[raw] = actor
    return mapping




def _estimate_natural_dialogue_seconds(turns: list[dict[str, Any]]) -> float:
    """V0.8 authoring estimate: useful guard, not a reason to create dead air.

    V6.8 measures actual generated WAVs and is the final source of truth. This
    estimator is intentionally closer to conversational Hindi than the old 4s floor.
    """
    texts = [str(t.get("text") or "").strip() for t in turns if str(t.get("text") or "").strip()]
    if not texts:
        return 2.0
    joined = " ".join(texts)
    words = [w for w in joined.replace("\n", " ").split(" ") if w.strip()]
    visible_chars = sum(1 for ch in joined if not ch.isspace())
    speech = max(len(words) * 0.38, visible_chars / 9.0, 1.15)
    pauses = sum(max(0.05, min(0.35, float(t.get("pause_after_seconds") or 0.075))) for t in turns)
    return round(max(2.0, speech + pauses + 0.22), 2)


def _autofit_scene_duration(requested_seconds: float, turns: list[dict[str, Any]]) -> float:
    requested = max(2.0, float(requested_seconds))
    if not turns:
        return round(requested, 2)
    natural = _estimate_natural_dialogue_seconds(turns)
    # Grow undersized scenes, but also shrink legacy over-sized safety slots.
    if requested < natural - 0.05:
        return round(natural, 2)
    if requested > natural + 0.90:
        return round(natural, 2)
    return round(requested, 2)


def timing_report_for_scenes(scenes) -> list[dict[str, Any]]:
    report: list[dict[str, Any]] = []
    for scene in sorted(scenes, key=lambda x: x.order_index):
        meta = scene.metadata_json or {}
        turns = meta.get("dialogue_turns") or []
        requested = round(float(scene.duration_seconds), 2)
        recommended = _autofit_scene_duration(requested, turns)
        delta = round(recommended - requested, 2)
        report.append({
            "scene_id": scene.id,
            "scene_number": int(scene.order_index) + 1,
            "requested_seconds": requested,
            "recommended_seconds": recommended,
            "delta_seconds": delta,
            "status": "RISK" if delta > 0.01 else "OK",
            "dialogue_turns": len(turns),
        })
    return report






SUPPORTED_BLENDER_ACTIONS_V08 = {
    "walk", "enter", "run", "chase", "give", "show", "point", "use", "facepalm",
    "snatch_phone", "phone_pass", "whisper", "interview_sit", "ai_interview",
    "show_wedding_card", "offer_sweets", "backpedal", "wedding_prep", "mock_shock",
    "end_screen_hold", "phone_use", "drink", "clean", "carry", "announce", "serve",
}


def _infer_props_v08(context: str, idx: int, comedy: bool) -> list[str]:
    c = str(context or "").lower()
    if any(x in c for x in ("ai", "phone", "mobile", "assistant", "बहू", "फोन")):
        return ["ai_phone"]
    if any(x in c for x in ("wedding", "shaadi", "marriage", "शादी", "कार्ड")):
        return ["wedding_card"]
    if any(x in c for x in ("mithai", "sweet", "मिठाई")):
        return ["mithai_box"]
    if any(x in c for x in ("chai", "tea", "चाय")):
        return ["cup"]
    if any(x in c for x in ("parcel", "bag", "box", "बैग", "पार्सल")):
        return ["bag"]
    return ["chai_glass" if idx % 2 else "charpai"] if comedy else []


def _normalize_action_v08(explicit: str, context: str, idx: int, comedy: bool) -> str:
    action = str(explicit or "").strip().lower()
    if action in SUPPORTED_BLENDER_ACTIONS_V08:
        return action
    c = f"{action} {context}".lower()
    if any(x in c for x in ("snatch", "grab phone", "छीन", "फोन छीन")):
        return "snatch_phone"
    if any(x in c for x in ("pass phone", "hand phone", "फोन दे", "फोन पकड़")):
        return "phone_pass"
    if any(x in c for x in ("whisper", "secret", "कान में", "फुसफुस")):
        return "whisper"
    if any(x in c for x in ("interview", "पूछताछ", "सवाल")):
        return "ai_interview"
    if any(x in c for x in ("shock", "recoil", "reveal", "surprise", "चौंक")):
        return "mock_shock"
    if any(x in c for x in ("wedding card", "invite", "शादी कार्ड")):
        return "show_wedding_card"
    if any(x in c for x in ("sweet", "mithai", "मिठाई")):
        return "offer_sweets"
    if any(x in c for x in ("back", "retreat", "पीछे")):
        return "backpedal"
    if comedy:
        cycle = ["mock_shock", "snatch_phone", "whisper", "phone_pass", "ai_interview", "backpedal", "offer_sweets"]
        return cycle[(idx - 1) % len(cycle)]
    return "show"


def _pause_variation(scene_number: int, base: float, spread: float = 0.025) -> float:
    # Deterministic micro-variation avoids a metronomic edit rhythm while keeping tests stable.
    offsets = (-1.0, -0.35, 0.45, 0.9, 0.15)
    return round(max(0.02, base + offsets[(scene_number - 1) % len(offsets)] * spread), 3)


def _intra_turn_pause_v08(text: str, emotion: str, turn_index: int) -> float:
    text = str(text or '').strip()
    emotion = str(emotion or '').lower()
    if emotion in {'shocked', 'shock', 'angry', 'excited', 'laugh', 'happy'}:
        base = 0.16
    elif text.endswith(('?', '?!', '।?')):
        base = 0.13
    elif text.endswith(('!', '!!')):
        base = 0.15
    else:
        base = 0.075
    return _pause_variation(turn_index, base, 0.018)


def _transition_v08(current_scene, next_scene, scene_number: int, visual_action: str, comedy: bool) -> tuple[str, float, float]:
    """Return transition type, intentional reaction hold, and J-cut audio lead."""
    if next_scene is None:
        return 'end_hold', _pause_variation(scene_number, 0.34, 0.035), 0.0
    cur_meta = current_scene.metadata_json or {}
    nxt_meta = next_scene.metadata_json or {}
    cur_loc = str(cur_meta.get('location_id') or 'courtyard')
    nxt_loc = str(nxt_meta.get('location_id') or 'courtyard')
    beat = str(cur_meta.get('beat') or '').lower()
    if cur_loc != nxt_loc:
        return 'location_cut', _pause_variation(scene_number, 0.30, 0.04), 0.0
    if 'dialogue' in beat and comedy:
        return 'continuous_dialogue', _pause_variation(scene_number, 0.065, 0.02), _pause_variation(scene_number, 0.11, 0.018)
    if any(x in beat for x in ('punch', 'payoff', 'twist', 'reveal')) or visual_action in {'mock_shock', 'offer_sweets'}:
        return 'punchline_hold', _pause_variation(scene_number, 0.27, 0.045), 0.0
    if visual_action in {'backpedal', 'whisper', 'snatch_phone', 'ai_interview'}:
        return 'reaction_hold', _pause_variation(scene_number, 0.19, 0.035), 0.025
    if comedy:
        return 'continuous_dialogue', _pause_variation(scene_number, 0.065, 0.02), _pause_variation(scene_number, 0.11, 0.018)
    return 'normal_cut', _pause_variation(scene_number, 0.10, 0.025), 0.05


def project_to_agentic_plan(project, scenes) -> dict[str, Any]:
    characters: list[str] = []
    output_scenes: list[dict[str, Any]] = []
    speaker_map = _map_speakers_for_blender(scenes)

    ordered_scenes = sorted(scenes, key=lambda x: x.order_index)
    for idx, scene in enumerate(ordered_scenes, start=1):
        next_scene = ordered_scenes[idx] if idx < len(ordered_scenes) else None
        meta = scene.metadata_json or {}
        turns = meta.get("dialogue_turns") or []
        normalized_turns = []
        for turn in turns:
            raw_speaker = _speaker_alias(str(turn.get("speaker") or "narrator"))
            speaker = speaker_map.get(raw_speaker, raw_speaker)
            if speaker != "narrator" and speaker not in characters:
                characters.append(speaker)
            text = str(turn.get("text") or "").strip()
            if text:
                emotion = str(turn.get("emotion") or "neutral").lower()
                normalized_turns.append({
                    "character_id": speaker,
                    "text": text,
                    "emotion": emotion,
                    "pose": str(turn.get("pose") or "idle").lower(),
                    "pause_after_seconds": _intra_turn_pause_v08(text, emotion, len(normalized_turns) + 1),
                })
        if not normalized_turns and scene.dialogue.strip():
            # The renderer can play narrator audio, but a visible actor gives a much
            # more useful preview than a silent/motionless cast.
            fallback_actor = BLENDER_ACTORS[(idx - 1) % len(BLENDER_ACTORS)]
            if fallback_actor not in characters:
                characters.append(fallback_actor)
            normalized_turns.append({
                "character_id": fallback_actor,
                "text": scene.dialogue.strip(),
                "emotion": "neutral",
                "pose": "idle",
                "pause_after_seconds": _intra_turn_pause_v08(scene.dialogue.strip(), "neutral", 1),
            })

        comedy = "kanpuri" in str(project.style).lower() or "comedy" in str(project.style).lower()
        context = f"{project.prompt} {scene.visual_prompt} {meta.get('setup','')}".lower()
        props = list(meta.get("props") or [])
        if not props:
            props = _infer_props_v08(context, idx, comedy)
        visual_action = _normalize_action_v08(str(meta.get("visual_action") or "dialogue"), context, idx, comedy)
        camera_cycle = ["speaker_close_up", "speaker_close_up", "speaker_medium", "speaker_medium", "speaker_close_up", "speaker_medium"]
        camera = str(meta.get("camera") or "speaker_medium")
        if comedy and (idx == 1 or camera == "speaker_medium"):
            camera = camera_cycle[(idx - 1) % len(camera_cycle)]
        blocking = list(meta.get("blocking") or [])
        if comedy and not blocking:
            blocking = [
                {"character":"babuji","action":visual_action,"strength":1.0},
                {"character":"guddu","action":"approach_or_recoil","strength":0.8},
                {"character":"bittu","action":"listener_reaction_or_whisper","strength":0.9},
            ]
        expressions = list(meta.get("expression_beats") or [])
        if comedy and not expressions:
            expressions = [
                {"character":"babuji","emotion":"shock" if idx == 1 else "confused","at":0.22},
                {"character":"guddu","emotion":"worried","at":0.48},
                {"character":"bittu","emotion":"smug","at":0.68},
            ]
        transition_type, transition_pause, j_cut = _transition_v08(scene, next_scene, idx, visual_action, comedy)
        # The last spoken turn owns the scene-boundary reaction beat. No extra fixed tail is added later.
        if normalized_turns:
            normalized_turns[-1]["pause_after_seconds"] = transition_pause
        output_scenes.append({
            "id": idx,
            "location_id": str(meta.get("location_id") or "courtyard"),
            "beat": str(meta.get("beat") or ("cold_open" if idx == 1 else "scene")),
            "camera": camera,
            "shot_duration_seconds": _autofit_scene_duration(float(scene.duration_seconds), normalized_turns),
            "setup": str(meta.get("setup") or scene.visual_prompt),
            "dialogue": normalized_turns,
            "visual_action": visual_action,
            "props": props,
            "visual_characters": list(meta.get("visual_characters") or (list(BLENDER_ACTORS) if comedy else [])),
            "blocking": blocking,
            "expression_beats": expressions,
            "lip_sync_mode": str(meta.get("lip_sync_mode") or ("viseme_ready_v07" if comedy else "speech_reactive")),
            "story_prop_required": bool(meta.get("story_prop_required", comedy)),
            "hero_insert": "ai_phone_close_up" if comedy and idx == 1 and "ai_phone" in props else None,
            "hero_insert_seconds": 1.75 if comedy and idx == 1 and "ai_phone" in props else 0.0,
            "performance_lock_v63": bool(comedy and idx <= 3),
            "camera_action": "dialogue_motivated_3d",
            "transition": transition_type,
            "transition_after": transition_type,
            "transition_pause_seconds": transition_pause,
            "j_cut_seconds": j_cut,
            "timing_mode": "adaptive_dialogue_v08",
            "ambient_continuity": True,
            "max_unexplained_dead_air_seconds": 0.45,
            "environment_variant": f"bharatvideo_scene_{idx}",
            "blocking_mode": "action",
        })

    if "kanpuri" in str(project.style).lower() or "comedy" in str(project.style).lower():
        characters = list(BLENDER_ACTORS)
    elif not characters:
        characters = list(BLENDER_ACTORS)

    first_meta = (scenes[0].metadata_json or {}) if scenes else {}
    return {
        "title": project.title,
        "topic": project.prompt,
        "language_code": "hindi" if project.language.startswith("hi") else project.language,
        "language_name": project.dialect or project.language,
        "genre": project.style or "family_comedy",
        "characters": characters[:3],
        "story_engine": {
            "source": "bharatvideo_ai_mvp_v0_8",
            "fresh_story": True,
            "dialect": project.dialect,
            "running_joke": first_meta.get("running_joke", ""),
            "twist": first_meta.get("twist", ""),
            "old_plan_autodiscovery": False,
            "blender_actor_map": speaker_map,
            "natural_speech_duration_autofit": True,
            "performance_lock_v07": True,
            "three_character_comedy_lock": True,
            "story_prop_blocking": True,
            "adaptive_scene_timing_v08": True,
            "adaptive_pause_engine_v08": True,
            "j_l_cut_audio_v08": True,
            "tts_edge_silence_trim_v08": True,
            "max_unexplained_dead_air_seconds": 0.45,
        },
        "scenes": output_scenes,
    }
