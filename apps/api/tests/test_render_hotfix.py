from types import SimpleNamespace

from app.services.engine_plan import project_to_agentic_plan


def scene(order_index, speaker):
    return SimpleNamespace(
        order_index=order_index,
        duration_seconds=6.0,
        dialogue=f"{speaker}: test",
        visual_prompt="test visual",
        generation_mode="BLENDER_3D",
        metadata_json={
            "dialogue_turns": [{"speaker": speaker, "text": "test line", "emotion": "shocked", "pose": "pointing"}],
            "camera": "speaker_medium",
            "visual_action": "dialogue",
            "props": [],
        },
    )


def project():
    return SimpleNamespace(
        title="Render Hotfix",
        prompt="Test app-generated speakers",
        language="hi-IN",
        dialect="hinglish",
        style="funny",
    )


def test_unknown_llm_speakers_are_mapped_to_stable_blender_rigs():
    plan = project_to_agentic_plan(project(), [scene(0, "shopkeeper"), scene(1, "customer"), scene(2, "manager")])
    assert plan["characters"] == ["babuji", "guddu", "bittu"]
    assert [s["dialogue"][0]["character_id"] for s in plan["scenes"]] == ["babuji", "guddu", "bittu"]
    assert plan["story_engine"]["blender_actor_map"] == {
        "shopkeeper": "babuji",
        "customer": "guddu",
        "manager": "bittu",
    }


def test_known_blender_speakers_are_preserved():
    plan = project_to_agentic_plan(project(), [scene(0, "Babuji"), scene(1, "Guddua"), scene(2, "Bittua")])
    assert [s["dialogue"][0]["character_id"] for s in plan["scenes"]] == ["babuji", "guddu", "bittu"]


def test_narrator_only_scene_gets_visible_actor_for_preview():
    s = SimpleNamespace(
        order_index=0,
        duration_seconds=4.0,
        dialogue="Narration line",
        visual_prompt="visual",
        generation_mode="TEMPLATE",
        metadata_json={},
    )
    plan = project_to_agentic_plan(project(), [s])
    assert plan["scenes"][0]["dialogue"][0]["character_id"] == "babuji"


def test_dense_dialogue_auto_expands_three_second_scene():
    dense = SimpleNamespace(
        order_index=0, duration_seconds=3.0, dialogue="dense", visual_prompt="visual", generation_mode="BLENDER_3D",
        metadata_json={"dialogue_turns": [{"speaker": "Babuji", "text": "का बे Guddua ई फोनवा में कौन अंगरेजन बैठी है हमका अभी सब सच सच बताय द्यो", "emotion": "shocked", "pose": "pointing"}]},
    )
    plan = project_to_agentic_plan(project(), [dense])
    assert plan["scenes"][0]["shot_duration_seconds"] >= 5.0
    assert plan["story_engine"]["natural_speech_duration_autofit"] is True


def test_v08_short_dialogue_shrinks_legacy_oversized_budget():
    short = SimpleNamespace(
        order_index=0, duration_seconds=6.0, dialogue="short", visual_prompt="visual", generation_mode="BLENDER_3D",
        metadata_json={"dialogue_turns": [{"speaker": "Babuji", "text": "का बे?", "emotion": "shocked", "pose": "idle"}]},
    )
    plan = project_to_agentic_plan(project(), [short])
    assert 2.0 <= plan["scenes"][0]["shot_duration_seconds"] < 4.0
