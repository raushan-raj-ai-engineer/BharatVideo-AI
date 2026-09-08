from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models import GenerationJob, Project, ProjectOwner, ProjectStatus, Scene, User
from app.schemas.project import EngineRenderRequest, JobRead, ProjectCreate, ProjectRead
from app.services.cost_estimator import estimate_credits
from app.services.security import debit_credits, get_current_user, require_project_access
from app.services.engine_plan import project_to_agentic_plan, timing_report_for_scenes
from app.tasks.generation import generate_project, render_project

router = APIRouter(prefix="/v1/projects", tags=["projects"])


def _project_stmt():
    return select(Project).options(
        selectinload(Project.scenes).selectinload(Scene.media_assets),
        selectinload(Project.artifacts),
        selectinload(Project.media_assets),
    )


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = Project(**payload.model_dump(), estimated_credits=estimate_credits(payload))
    db.add(project)
    db.flush()
    db.add(ProjectOwner(user_id=user.id, project_id=project.id))
    db.commit()
    return db.scalar(_project_stmt().where(Project.id == project.id))


@router.get("", response_model=list[ProjectRead])
def list_projects(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = _project_stmt().join(ProjectOwner, ProjectOwner.project_id == Project.id).where(ProjectOwner.user_id == user.id).order_by(Project.created_at.desc())
    return list(db.scalars(stmt).unique().all())


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_project_access(db, user.id, project_id)
    project = db.scalar(_project_stmt().where(Project.id == project_id))
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.post("/{project_id}/generate", response_model=JobRead, status_code=status.HTTP_202_ACCEPTED)
def queue_generation(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = require_project_access(db, user.id, project_id)
    debit_credits(db, user.id, 2, "GENERATION", "Story + scene planning", f"generate:{project.id}:{project.updated_at.isoformat()}")
    job = GenerationJob(project_id=project.id)
    project.status = ProjectStatus.QUEUED
    db.add(job)
    db.commit()
    db.refresh(job)
    async_result = generate_project.delay(job.id)
    job.celery_task_id = async_result.id
    db.commit()
    db.refresh(job)
    return job


@router.get("/{project_id}/engine-plan")
def export_engine_plan(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = require_project_access(db, user.id, project_id)
    scenes = list(db.scalars(select(Scene).where(Scene.project_id == project.id).order_by(Scene.order_index)).all())
    if not scenes:
        raise HTTPException(409, "Generate scenes before exporting an engine plan")
    return project_to_agentic_plan(project, scenes)


@router.post("/{project_id}/render", response_model=JobRead, status_code=status.HTTP_202_ACCEPTED)
def queue_render(project_id: str, payload: EngineRenderRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = require_project_access(db, user.id, project_id)
    # A simple existence check is enough before dispatching the render job.
    if not db.scalar(select(Scene.id).where(Scene.project_id == project.id).limit(1)):
        raise HTTPException(409, "Generate scenes before rendering")
    render_cost = 8 if payload.mode == "preview" else (35 if payload.quality == "draft" else 60)
    debit_credits(db, user.id, render_cost, "RENDER", f"{payload.mode.title()} 3D render", f"render:{project.id}:{payload.mode}:{project.updated_at.isoformat()}")
    job = GenerationJob(project_id=project.id)
    project.status = ProjectStatus.QUEUED
    db.add(job)
    db.commit()
    db.refresh(job)
    async_result = render_project.delay(job.id, payload.mode, payload.quality)
    job.celery_task_id = async_result.id
    db.commit()
    db.refresh(job)
    return job


@router.get("/{project_id}/timing")
def project_timing(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = require_project_access(db, user.id, project_id)
    scenes = list(db.scalars(select(Scene).where(Scene.project_id == project.id).order_by(Scene.order_index)).all())
    report = timing_report_for_scenes(scenes)
    return {
        "project_id": project_id,
        "status": "RISK" if any(x["status"] == "RISK" for x in report) else "OK",
        "total_requested_seconds": round(sum(x["requested_seconds"] for x in report), 2),
        "total_recommended_seconds": round(sum(x["recommended_seconds"] for x in report), 2),
        "scenes": report,
    }


@router.post("/{project_id}/autofit-timing")
def autofit_project_timing(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = require_project_access(db, user.id, project_id)
    scenes = list(db.scalars(select(Scene).where(Scene.project_id == project.id).order_by(Scene.order_index)).all())
    before = timing_report_for_scenes(scenes)
    changed = []
    for scene, item in zip(scenes, before):
        recommended = float(item["recommended_seconds"])
        old = float(scene.duration_seconds)
        if abs(recommended - old) > 0.08:
            scene.duration_seconds = recommended
            changed.append({
                "scene_id": scene.id, "from": round(old, 2), "to": round(scene.duration_seconds, 2),
                "direction": "shrink" if recommended < old else "grow",
            })
    db.commit()
    return {"status": "OK", "changed": changed, "scene_count": len(scenes)}
