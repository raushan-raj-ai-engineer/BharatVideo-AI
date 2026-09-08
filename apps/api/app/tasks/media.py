from __future__ import annotations

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import AssetStatus, GenerationJob, JobStatus, MediaAsset, Project, ProjectArtifact, ProjectStatus, Scene
from app.services.media_pipeline import (
    compose_project_video,
    compose_scene_video,
    generate_image,
    generate_scene_srt,
    generate_project_srt,
    generate_voice,
)
from app.tasks.celery_app import celery


def _latest_asset(db, scene_id: str, kind: str) -> MediaAsset | None:
    stmt = (
        select(MediaAsset)
        .where(MediaAsset.scene_id == scene_id, MediaAsset.kind == kind, MediaAsset.status == AssetStatus.READY)
        .order_by(MediaAsset.created_at.desc())
    )
    return db.scalars(stmt).first()


def _add_asset(db, *, project_id: str, scene_id: str | None, kind: str, provider: str, url: str, cost_credits: int = 0, metadata: dict | None = None) -> MediaAsset:
    asset = MediaAsset(
        project_id=project_id,
        scene_id=scene_id,
        kind=kind,
        provider=provider,
        status=AssetStatus.READY,
        url=url,
        cost_credits=cost_credits,
        metadata_json=metadata or {},
    )
    db.add(asset)
    db.flush()
    return asset


def _generate_scene_media_sync(db, scene: Scene, project: Project, *, voice: str, speech_rate: int, force: bool) -> dict:
    created: dict[str, str] = {}

    image = None if force else _latest_asset(db, scene.id, "image")
    if not image:
        image_url, meta = generate_image(
            project_id=project.id,
            scene_id=scene.id,
            order_index=scene.order_index,
            prompt=scene.visual_prompt,
            aspect_ratio=project.aspect_ratio,
        )
        image = _add_asset(db, project_id=project.id, scene_id=scene.id, kind="image", provider="mock", url=image_url, metadata=meta)
    created["image"] = image.url

    voice_asset = None if force else _latest_asset(db, scene.id, "voice")
    if not voice_asset:
        voice_url, meta = generate_voice(
            project_id=project.id,
            scene_id=scene.id,
            text=scene.dialogue,
            voice=voice,
            rate=speech_rate,
        )
        voice_asset = _add_asset(db, project_id=project.id, scene_id=scene.id, kind="voice", provider=meta.get("provider", "local"), url=voice_url, metadata=meta)
    created["voice"] = voice_asset.url

    subtitle = None if force else _latest_asset(db, scene.id, "subtitle")
    if not subtitle:
        subtitle_url, meta = generate_scene_srt(
            project_id=project.id,
            scene_id=scene.id,
            dialogue=scene.dialogue,
            duration_seconds=scene.duration_seconds,
        )
        subtitle = _add_asset(db, project_id=project.id, scene_id=scene.id, kind="subtitle", provider="local_srt", url=subtitle_url, metadata=meta)
    created["subtitle"] = subtitle.url

    scene_video = None if force else _latest_asset(db, scene.id, "scene_video")
    if not scene_video:
        resolution = "1280x720" if project.aspect_ratio == "16:9" else "720x1280"
        video_url, meta = compose_scene_video(
            project_id=project.id,
            scene_id=scene.id,
            image_url=image.url,
            voice_url=voice_asset.url,
            duration_seconds=scene.duration_seconds,
            resolution=resolution,
        )
        scene_video = _add_asset(db, project_id=project.id, scene_id=scene.id, kind="scene_video", provider="ffmpeg", url=video_url, metadata=meta)
    created["scene_video"] = scene_video.url
    return created


@celery.task(name="generate_scene_media")
def generate_scene_media(job_id: str, scene_id: str, voice: str = "Lekha", speech_rate: int = 185, force: bool = False) -> dict:
    db = SessionLocal()
    job = project = None
    try:
        job = db.get(GenerationJob, job_id)
        if not job:
            raise RuntimeError(f"Job not found: {job_id}")
        scene = db.get(Scene, scene_id)
        if not scene:
            raise RuntimeError(f"Scene not found: {scene_id}")
        project = db.get(Project, scene.project_id)
        if not project:
            raise RuntimeError(f"Project not found: {scene.project_id}")
        job.status = JobStatus.RUNNING
        job.progress = 10
        project.status = ProjectStatus.GENERATING
        db.commit()
        result = _generate_scene_media_sync(db, scene, project, voice=voice, speech_rate=speech_rate, force=force)
        job.progress = 95
        db.commit()
        project.status = ProjectStatus.READY
        job.status = JobStatus.SUCCEEDED
        job.progress = 100
        db.commit()
        return {"job_id": job.id, "scene_id": scene.id, **result}
    except Exception as exc:
        if job:
            job.status = JobStatus.FAILED
            job.error = str(exc)
        if project:
            project.status = ProjectStatus.READY
        db.commit()
        raise
    finally:
        db.close()


@celery.task(name="generate_project_media")
def generate_project_media(job_id: str, voice: str = "Lekha", speech_rate: int = 185, force: bool = False) -> dict:
    db = SessionLocal()
    job = project = None
    try:
        job = db.get(GenerationJob, job_id)
        if not job:
            raise RuntimeError(f"Job not found: {job_id}")
        project = db.get(Project, job.project_id)
        if not project:
            raise RuntimeError(f"Project not found: {job.project_id}")
        scenes = list(db.scalars(select(Scene).where(Scene.project_id == project.id).order_by(Scene.order_index)).all())
        if not scenes:
            raise RuntimeError("Generate story scenes before media")
        job.status = JobStatus.RUNNING
        project.status = ProjectStatus.GENERATING
        job.progress = 5
        db.commit()
        results = []
        for idx, scene in enumerate(scenes, start=1):
            results.append(_generate_scene_media_sync(db, scene, project, voice=voice, speech_rate=speech_rate, force=force))
            job.progress = 5 + int((idx / len(scenes)) * 90)
            db.commit()
        project.status = ProjectStatus.READY
        job.status = JobStatus.SUCCEEDED
        job.progress = 100
        db.commit()
        return {"job_id": job.id, "project_id": project.id, "scene_count": len(results)}
    except Exception as exc:
        if job:
            job.status = JobStatus.FAILED
            job.error = str(exc)
        if project:
            project.status = ProjectStatus.READY
        db.commit()
        raise
    finally:
        db.close()


@celery.task(name="compose_project_media")
def compose_project_media(job_id: str, burn_subtitles: bool = True) -> dict:
    db = SessionLocal()
    job = project = None
    try:
        job = db.get(GenerationJob, job_id)
        if not job:
            raise RuntimeError(f"Job not found: {job_id}")
        project = db.get(Project, job.project_id)
        if not project:
            raise RuntimeError(f"Project not found: {job.project_id}")
        scenes = list(db.scalars(select(Scene).where(Scene.project_id == project.id).order_by(Scene.order_index)).all())
        if not scenes:
            raise RuntimeError("No scenes exist")
        job.status = JobStatus.RUNNING
        project.status = ProjectStatus.GENERATING
        job.progress = 15
        db.commit()

        videos: list[str] = []
        missing: list[int] = []
        for scene in scenes:
            asset = _latest_asset(db, scene.id, "scene_video")
            if asset:
                videos.append(asset.url)
            else:
                missing.append(scene.order_index + 1)
        if missing:
            raise RuntimeError(f"Scene videos missing for scenes: {missing}. Generate project media first.")

        job.progress = 55
        db.commit()
        subtitle_url, subtitle_meta = generate_project_srt(
            project_id=project.id,
            scenes=[(scene.dialogue, scene.duration_seconds) for scene in scenes],
        )
        _add_asset(db, project_id=project.id, scene_id=None, kind="subtitle", provider="local_srt", url=subtitle_url, metadata=subtitle_meta)
        url, meta = compose_project_video(project_id=project.id, scene_video_urls=videos, subtitle_url=subtitle_url, burn_subtitles=burn_subtitles)
        _add_asset(db, project_id=project.id, scene_id=None, kind="final_video", provider="ffmpeg", url=url, metadata=meta)
        db.add(ProjectArtifact(project_id=project.id, kind="local_media_preview", url=url, metadata_json=meta))
        project.status = ProjectStatus.READY
        job.status = JobStatus.SUCCEEDED
        job.progress = 100
        db.commit()
        return {"job_id": job.id, "project_id": project.id, "asset_url": url}
    except Exception as exc:
        if job:
            job.status = JobStatus.FAILED
            job.error = str(exc)
        if project:
            project.status = ProjectStatus.READY
        db.commit()
        raise
    finally:
        db.close()
