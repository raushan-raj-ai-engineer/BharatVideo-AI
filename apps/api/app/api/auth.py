from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models import Project, ProjectOwner, User
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserRead
from app.services.security import add_credits, credit_balance, get_current_user, hash_password, issue_token, verify_password

router = APIRouter(prefix="/v1/auth", tags=["auth"])


def _user_read(db: Session, user: User) -> UserRead:
    return UserRead(id=user.id, name=user.name, email=user.email, plan_id=user.plan_id, credits=credit_balance(db, user.id), created_at=user.created_at)


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Email already registered")
    first_user = int(db.scalar(select(func.count()).select_from(User)) or 0) == 0
    user = User(name=payload.name.strip(), email=email, password_hash=hash_password(payload.password))
    db.add(user); db.flush()
    settings = get_settings()
    add_credits(db, user.id, settings.signup_credits, "SIGNUP", "Welcome credits", f"signup:{user.id}")
    # First account safely claims legacy projects created before authentication existed.
    if first_user:
        owned = set(db.scalars(select(ProjectOwner.project_id)).all())
        for project_id in db.scalars(select(Project.id)).all():
            if project_id not in owned:
                db.add(ProjectOwner(user_id=user.id, project_id=project_id))
    db.commit(); db.refresh(user)
    return AuthResponse(token=issue_token(user), user=_user_read(db, user))


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower().strip()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    return AuthResponse(token=issue_token(user), user=_user_read(db, user))


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _user_read(db, user)
