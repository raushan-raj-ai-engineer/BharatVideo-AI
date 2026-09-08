from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models import Project, Scene

client = TestClient(app)


def create_project():
    response = client.post("/v1/projects", json={
        "title": "Kanpur Gym Reel",
        "prompt": "Create a funny Hinglish gym joining offer reel",
        "platform": "instagram_reel",
        "language": "hi-IN",
        "dialect": "hinglish",
        "duration_seconds": 30,
        "quality": "balanced",
    })
    assert response.status_code == 201
    return response.json()


def test_health_v03():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.8.0"
    assert body["llm_provider"] == "mock"
    assert body["tts_provider"] == "mock"
    assert body["image_provider"] == "mock"


def test_create_project():
    body = create_project()
    assert body["estimated_credits"] > 0
    assert body["status"] == "DRAFT"
    assert body["artifacts"] == []


def test_scene_patch_and_engine_plan_export():
    project = create_project()
    db = SessionLocal()
    try:
        row = db.get(Project, project["id"])
        scene = Scene(
            project_id=row.id,
            order_index=0,
            duration_seconds=6,
            dialogue="Babuji: का बे Guddua?",
            visual_prompt="Babuji points at a phone in a Kanpur courtyard",
            generation_mode="BLENDER_3D",
            metadata_json={
                "camera": "speaker_close_up",
                "visual_action": "point_phone",
                "props": ["ai_phone"],
                "dialogue_turns": [{"speaker": "babuji", "text": "का बे Guddua?", "emotion": "shocked", "pose": "pointing"}],
            },
        )
        db.add(scene)
        db.commit()
        db.refresh(scene)
        scene_id = scene.id
    finally:
        db.close()

    patched = client.patch(f"/v1/scenes/{scene_id}", json={"dialogue": "Babuji: ई का भौकाल है बे?"})
    assert patched.status_code == 200
    assert "भौकाल" in patched.json()["dialogue"]

    exported = client.get(f"/v1/projects/{project['id']}/engine-plan")
    assert exported.status_code == 200
    plan = exported.json()
    assert plan["story_engine"]["old_plan_autodiscovery"] is False
    assert plan["scenes"][0]["props"] == ["ai_phone"]
    assert plan["scenes"][0]["dialogue"][0]["character_id"] == "babuji"


def test_scene_regenerate_mock():
    project = create_project()
    db = SessionLocal()
    try:
        row = db.get(Project, project["id"])
        scene = Scene(
            project_id=row.id,
            order_index=0,
            duration_seconds=6,
            dialogue="Original line",
            visual_prompt="Simple visual prompt",
            generation_mode="TEMPLATE",
            metadata_json={},
        )
        db.add(scene); db.commit(); db.refresh(scene); scene_id=scene.id
    finally:
        db.close()
    response = client.post(f"/v1/scenes/{scene_id}/regenerate", json={"instruction": "Make it funnier"})
    assert response.status_code == 200
    assert "Mock rewrite" in response.json()["dialogue"]
