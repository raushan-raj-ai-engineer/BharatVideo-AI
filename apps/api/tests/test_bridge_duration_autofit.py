import importlib.util
from pathlib import Path

BRIDGE = Path(__file__).resolve().parents[3] / "engine_bridge" / "bridge_server.py"
spec = importlib.util.spec_from_file_location("bridge_server_v032", BRIDGE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_bridge_autofits_old_saved_plan_without_persisting_db():
    plan = {"scenes": [{
        "id": 2,
        "shot_duration_seconds": 3.0,
        "dialogue": [{"character_id": "babuji", "text": "का बे Guddua ई फोनवा में कौन अंगरेजन बैठी है हमका अभी सब सच सच बताय द्यो"}],
    }]}
    changes = mod._autofit_plan_dialogue_budgets(plan)
    assert changes
    assert plan["scenes"][0]["shot_duration_seconds"] >= 5.0


def test_v08_bridge_shrinks_legacy_65s_slot_when_plan_is_adaptive():
    plan = {
        "story_engine": {"adaptive_scene_timing_v08": True},
        "scenes": [{
            "id": 1,
            "shot_duration_seconds": 6.5,
            "timing_mode": "adaptive_dialogue_v08",
            "dialogue": [{"character_id": "babuji", "text": "का बे?", "pause_after_seconds": 0.07}],
        }],
    }
    changes = mod._autofit_plan_dialogue_budgets(plan)
    assert changes and changes[0]["direction"] == "shrink"
    assert 2.0 <= plan["scenes"][0]["shot_duration_seconds"] < 4.0
