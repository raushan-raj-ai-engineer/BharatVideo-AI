from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import GenerationJob, MediaAsset, Project, Scene, User
from app.schemas.project import ComposeRequest, JobRead, MediaAssetRead, ProjectMediaRequest, SceneMediaRequest
from app.tasks.media import compose_project_media, generate_project_media, generate_scene_media
from app.services.security import get_current_user, require_project_access

router = APIRouter(prefix="/v1", tags=["media"])


def _queue(db: Session, project_id: str) -> GenerationJob:
    job = GenerationJob(project_id=project_id)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("/projects/{project_id}/media", response_model=list[MediaAssetRead])
def list_project_media(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_project_access(db, user.id, project_id)
    stmt = select(MediaAsset).where(MediaAsset.project_id == project_id).order_by(MediaAsset.created_at.desc())
    return list(db.scalars(stmt).all())


@router.post("/scenes/{scene_id}/media", response_model=JobRead, status_code=status.HTTP_202_ACCEPTED)
def queue_scene_media(scene_id: str, payload: SceneMediaRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    scene = db.get(Scene, scene_id)
    if not scene:
        raise HTTPException(404, "Scene not found")
    require_project_access(db, user.id, scene.project_id)
    job = _queue(db, scene.project_id)
    result = generate_scene_media.delay(job.id, scene.id, payload.voice, payload.speech_rate, payload.force)
    job.celery_task_id = result.id
    db.commit(); db.refresh(job)
    return job


@router.post("/projects/{project_id}/media", response_model=JobRead, status_code=status.HTTP_202_ACCEPTED)
def queue_project_media(project_id: str, payload: ProjectMediaRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = require_project_access(db, user.id, project_id)
    if not db.scalar(select(Scene.id).where(Scene.project_id == project_id).limit(1)):
        raise HTTPException(409, "Generate story scenes before media")
    job = _queue(db, project_id)
    result = generate_project_media.delay(job.id, payload.voice, payload.speech_rate, payload.force)
    job.celery_task_id = result.id
    db.commit(); db.refresh(job)
    return job


@router.post("/projects/{project_id}/compose", response_model=JobRead, status_code=status.HTTP_202_ACCEPTED)
def queue_compose(project_id: str, payload: ComposeRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Draft/storyboard composition remains optional; production path is Blender 3D.
    project = require_project_access(db, user.id, project_id)
    job = _queue(db, project_id)
    result = compose_project_media.delay(job.id, payload.burn_subtitles)
    job.celery_task_id = result.id
    db.commit(); db.refresh(job)
    return job
