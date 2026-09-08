from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Project, Scene, User
from app.schemas.project import SceneRead, SceneRegenerateRequest, SceneUpdate
from app.services.scene_planner import regenerate_scene_content
from app.services.security import debit_credits, get_current_user, require_project_access

router = APIRouter(prefix="/v1/scenes", tags=["scenes"])


def _scene(db: Session, user: User, scene_id: str) -> Scene:
    scene = db.get(Scene, scene_id)
    if not scene:
        raise HTTPException(404, "Scene not found")
    require_project_access(db, user.id, scene.project_id)
    return scene


@router.get("/{scene_id}", response_model=SceneRead)
def get_scene(scene_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _scene(db, user, scene_id)


@router.patch("/{scene_id}", response_model=SceneRead)
def update_scene(scene_id: str, payload: SceneUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    scene = _scene(db, user, scene_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(scene, key, value)
    db.commit(); db.refresh(scene)
    return scene


@router.post("/{scene_id}/regenerate", response_model=SceneRead)
def regenerate_scene(scene_id: str, payload: SceneRegenerateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    scene = _scene(db, user, scene_id)
    project = db.get(Project, scene.project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    debit_credits(db, user.id, 1, "GENERATION", "Regenerate one scene", f"scene:{scene.id}:{scene.duration_seconds}")
    current = {"order_index": scene.order_index, "duration_seconds": scene.duration_seconds, "dialogue": scene.dialogue, "visual_prompt": scene.visual_prompt, "generation_mode": scene.generation_mode, "metadata": scene.metadata_json or {}}
    try:
        updated = regenerate_scene_content(prompt=project.prompt, language=project.language, dialect=project.dialect, style=project.style, current_scene=current, instruction=payload.instruction)
    except Exception as exc:
        db.rollback()
        raise HTTPException(502, f"Scene regeneration failed: {exc}") from exc
    scene.duration_seconds = updated.duration_seconds
    scene.dialogue = updated.dialogue
    scene.visual_prompt = updated.visual_prompt
    scene.generation_mode = updated.generation_mode
    scene.metadata_json = {**(scene.metadata_json or {}), **updated.metadata}
    db.commit(); db.refresh(scene)
    return scene
