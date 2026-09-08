from __future__ import annotations

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import GenerationJob, JobStatus, Project, ProjectArtifact, ProjectStatus, Scene
from app.services.engine_bridge import EngineBridgeClient
from app.services.engine_plan import project_to_agentic_plan
from app.services.scene_planner import plan_story
from app.services.storage import LocalStorage
from app.tasks.celery_app import celery


@celery.task(name="generate_project")
def generate_project(job_id: str) -> dict:
    db = SessionLocal()
    storage = LocalStorage()
    job = project = None
    try:
        job = db.get(GenerationJob, job_id)
        if not job:
            raise RuntimeError(f"Job not found: {job_id}")
        project = db.get(Project, job.project_id)
        if not project:
            raise RuntimeError(f"Project not found: {job.project_id}")

        job.status = JobStatus.RUNNING
        project.status = ProjectStatus.GENERATING
        job.progress = 8
        db.commit()

        story = plan_story(
            project.prompt,
            project.duration_seconds,
            project.language,
            project.dialect,
            project.style,
        )
        job.progress = 35
        db.commit()

        existing = db.scalars(select(Scene).where(Scene.project_id == project.id)).all()
        for scene in existing:
            db.delete(scene)
        db.commit()

        total = len(story.scenes)
        for idx, p in enumerate(story.scenes, start=1):
            metadata = dict(p.metadata)
            metadata.update({
                "story_title": story.title,
                "story_hook": story.hook,
                "running_joke": story.running_joke,
                "twist": story.twist,
                "characters": story.characters,
                "planner_provider": story.provider,
                "planner_model": story.model,
                "planner_fallback_used": story.fallback_used,
                "planner_fallback_reason": story.fallback_reason,
            })
            url = storage.write_text_asset(
                f"projects/{project.id}/scenes/scene_{p.order_index + 1:02d}.txt",
                f"DIALOGUE\n{p.dialogue}\n\nVISUAL PROMPT\n{p.visual_prompt}\n",
            )
            db.add(Scene(
                project_id=project.id,
                order_index=p.order_index,
                duration_seconds=p.duration_seconds,
                dialogue=p.dialogue,
                visual_prompt=p.visual_prompt,
                generation_mode=p.generation_mode,
                asset_url=url,
                metadata_json=metadata,
            ))
            job.progress = 35 + int((idx / total) * 55)
            db.commit()

        project.title = story.title or project.title
        project.status = ProjectStatus.READY
        job.status = JobStatus.SUCCEEDED
        job.progress = 100
        db.commit()
        return {
            "job_id": job.id,
            "project_id": project.id,
            "status": "SUCCEEDED",
            "provider": story.provider,
            "model": story.model,
            "fallback_used": story.fallback_used,
        }
    except Exception as exc:
        if job:
            job.status = JobStatus.FAILED
            job.error = str(exc)
        if project:
            project.status = ProjectStatus.FAILED
        db.commit()
        raise
    finally:
        db.close()


@celery.task(name="render_project")
def render_project(job_id: str, mode: str = "preview", quality: str = "draft") -> dict:
    db = SessionLocal()
    storage = LocalStorage()
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
            raise RuntimeError("Generate scenes before rendering")

        job.status = JobStatus.RUNNING
        job.progress = 10
        project.status = ProjectStatus.GENERATING
        db.commit()

        plan = project_to_agentic_plan(project, scenes)
        job.progress = 20
        db.commit()

        bridge = EngineBridgeClient()
        max_scenes = 3 if mode == "preview" else None
        result = bridge.render(plan=plan, quality=quality, max_scenes=max_scenes)
        job.progress = 88
        db.commit()

        asset_id = result.get("asset_id")
        if not asset_id:
            raise RuntimeError(f"Engine bridge returned no asset_id: {result}")
        video_bytes = bridge.download_asset(str(asset_id))
        filename = "engine_preview.mp4" if mode == "preview" else "engine_full.mp4"
        url = storage.write_bytes_asset(f"projects/{project.id}/renders/{job.id}_{filename}", video_bytes)
        db.add(ProjectArtifact(
            project_id=project.id,
            kind=f"engine_{mode}",
            url=url,
            metadata_json={
                "bridge_asset_id": asset_id,
                "quality": quality,
                "mode": mode,
                "source_output": result.get("output_file"),
                "duration_autofit": result.get("duration_autofit", []),
                "bridge_version": "0.8.0",
            },
        ))
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
