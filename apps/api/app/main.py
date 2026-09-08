from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.engine import router as engine_router
from app.api.jobs import router as jobs_router
from app.api.media import router as media_router
from app.api.projects import router as projects_router
from app.api.providers import router as providers_router
from app.api.analytics import router as analytics_router
from app.api.auth import router as auth_router
from app.api.billing import router as billing_router
from app.api.scenes import router as scenes_router
from app.core.config import get_settings
from app.db.session import Base, engine
import app.models  # noqa: F401

settings = get_settings()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="BharatVideo AI API", version="0.8.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(billing_router)
app.include_router(projects_router)
app.include_router(scenes_router)
app.include_router(jobs_router)
app.include_router(engine_router)
app.include_router(media_router)
app.include_router(providers_router)
app.include_router(analytics_router)

storage_path = Path(settings.local_storage_dir)
storage_path.mkdir(parents=True, exist_ok=True)
app.mount("/assets", StaticFiles(directory=str(storage_path)), name="assets")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "bharatvideo-api",
        "version": "0.8.0",
        "llm_provider": settings.llm_provider,
        "llm_model": settings.ollama_model if settings.llm_provider == "ollama" else settings.llm_provider,
        "engine_mode": settings.engine_mode,
        "tts_provider": settings.tts_provider,
        "image_provider": settings.image_provider,
        "billing_mode": settings.billing_mode,
    }
