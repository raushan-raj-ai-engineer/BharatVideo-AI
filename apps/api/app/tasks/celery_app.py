from celery import Celery
from app.core.config import get_settings

settings = get_settings()
celery = Celery(
    "bharatvideo",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.generation", "app.tasks.media"],
)
celery.conf.task_track_started = True
celery.conf.result_expires = 3600
