from fastapi import APIRouter
from app.services.providers import provider_status

router = APIRouter(prefix="/v1/providers", tags=["providers"])

@router.get("")
def providers():
    return provider_status()
