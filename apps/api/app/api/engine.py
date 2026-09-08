from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.services.engine_bridge import EngineBridgeClient, EngineBridgeError

router = APIRouter(prefix="/v1/engine", tags=["engine"])


@router.get("/health")
def engine_health():
    settings = get_settings()
    if settings.engine_mode == "disabled":
        return {"status": "disabled"}
    try:
        return EngineBridgeClient().health()
    except EngineBridgeError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.post("/preflight")
def engine_preflight():
    settings = get_settings()
    if settings.engine_mode == "disabled":
        return {"status": "disabled"}
    try:
        return EngineBridgeClient().preflight()
    except EngineBridgeError as exc:
        raise HTTPException(503, str(exc)) from exc
