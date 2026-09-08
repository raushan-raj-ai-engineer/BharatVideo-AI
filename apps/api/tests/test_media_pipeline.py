from pathlib import Path

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models import GenerationJob, MediaAsset, Project, Scene
from app.services.media_pipeline import compose_project_video, compose_scene_video, generate_image, generate_project_srt, generate_scene_srt, generate_voice

client = TestClient(app)


def _seed_scene():
    db = SessionLocal()
    try:
        project = Project(
            title="Local Media Test",
            prompt="Funny gym reel",
            duration_seconds=5,
            aspect_ratio="9:16",
            language="hi-IN",
            dialect="hinglish",
            style="funny",
        )
        db.add(project); db.flush()
        scene = Scene(
            project_id=project.id,
            order_index=0,
            duration_seconds=3.0,
            dialogue="Hello BharatVideo. Local media test.",
            visual_prompt="Indian creator presenting a funny local business reel",
            generation_mode="TEMPLATE",
            metadata_json={},
        )
        db.add(scene); db.commit(); db.refresh(project); db.refresh(scene)
        return project.id, scene.id
    finally:
        db.close()


def test_media_queue_endpoints_are_available():
    project_id, scene_id = _seed_scene()
    scene_response = client.post(f"/v1/scenes/{scene_id}/media", json={"voice":"Lekha","speech_rate":185})
    assert scene_response.status_code == 202
    assert scene_response.json()["project_id"] == project_id

    project_response = client.post(f"/v1/projects/{project_id}/media", json={"voice":"Lekha","speech_rate":185})
    assert project_response.status_code == 202

    compose_response = client.post(f"/v1/projects/{project_id}/compose", json={"burn_subtitles":True,"resolution":"720x1280"})
    assert compose_response.status_code == 202


def test_local_media_services_create_playable_assets():
    project_id, scene_id = _seed_scene()
    image_url, image_meta = generate_image(
        project_id=project_id, scene_id=scene_id, order_index=0,
        prompt="A clean local mock visual", aspect_ratio="9:16",
    )
    voice_url, voice_meta = generate_voice(
        project_id=project_id, scene_id=scene_id, text="Local voice test", voice="Lekha", rate=185,
    )
    subtitle_url, subtitle_meta = generate_scene_srt(
        project_id=project_id, scene_id=scene_id, dialogue="Local caption test.", duration_seconds=3.0,
    )
    video_url, video_meta = compose_scene_video(
        project_id=project_id, scene_id=scene_id, image_url=image_url, voice_url=voice_url,
        duration_seconds=3.0, resolution="360x640",
    )
    project_srt_url, _ = generate_project_srt(project_id=project_id, scenes=[("Local caption test.", 3.0)])
    final_url, final_meta = compose_project_video(
        project_id=project_id, scene_video_urls=[video_url], subtitle_url=project_srt_url, burn_subtitles=False,
    )

    assert image_url.endswith("visual.png")
    assert voice_url.endswith("voice.wav")
    assert subtitle_url.endswith("captions.srt")
    assert video_url.endswith("scene.mp4")
    assert final_url.endswith("final_local_preview.mp4")
    assert image_meta["provider"] == "mock"
    assert voice_meta["provider"] == "mock"
    assert subtitle_meta["segments"] >= 1
    assert video_meta["provider"] == "ffmpeg"
    assert final_meta["scene_count"] == 1


def test_media_assets_are_returned_in_project_contract():
    project_id, scene_id = _seed_scene()
    db = SessionLocal()
    try:
        db.add(MediaAsset(
            project_id=project_id,
            scene_id=scene_id,
            kind="image",
            provider="mock",
            url="http://localhost:8000/assets/example.png",
            cost_credits=0,
            metadata_json={"test": True},
        ))
        db.commit()
    finally:
        db.close()
    response = client.get(f"/v1/projects/{project_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["media_assets"][0]["kind"] == "image"
    assert body["scenes"][0]["media_assets"][0]["provider"] == "mock"
