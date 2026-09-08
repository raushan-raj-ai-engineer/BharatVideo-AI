from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import CreditLedger, MediaAsset, Project, ProjectOwner, ProjectStatus, Scene, User
from app.services.security import get_current_user, credit_balance

router = APIRouter(prefix="/v1/analytics", tags=["analytics"])

@router.get("/summary")
def summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    owned_ids = select(ProjectOwner.project_id).where(ProjectOwner.user_id == user.id)
    projects = int(db.scalar(select(func.count()).select_from(Project).where(Project.id.in_(owned_ids))) or 0)
    scenes = int(db.scalar(select(func.count()).select_from(Scene).where(Scene.project_id.in_(owned_ids))) or 0)
    assets = int(db.scalar(select(func.count()).select_from(MediaAsset).where(MediaAsset.project_id.in_(owned_ids))) or 0)
    used = int(-(db.scalar(select(func.coalesce(func.sum(CreditLedger.amount), 0)).where(CreditLedger.user_id == user.id, CreditLedger.amount < 0)) or 0))
    ready = int(db.scalar(select(func.count()).select_from(Project).where(Project.id.in_(owned_ids), Project.status == ProjectStatus.READY)) or 0)
    return {"projects": projects, "scenes": scenes, "media_assets": assets, "credits_used": used, "credits_balance": credit_balance(db, user.id), "ready_projects": ready, "plan_id": user.plan_id}
