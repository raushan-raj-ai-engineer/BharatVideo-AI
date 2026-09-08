import os
import sys
import types
from pathlib import Path

os.environ["APP_ENV"] = "test"
os.environ["AUTH_SECRET"] = "test-secret"
os.environ["DATABASE_URL"] = "sqlite:///./test_bharatvideo_v03.db"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"
os.environ["LOCAL_STORAGE_DIR"] = "./test_storage_v03"
os.environ["PUBLIC_ASSET_BASE_URL"] = "http://localhost:8000/assets"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["ENGINE_MODE"] = "disabled"
os.environ["TTS_PROVIDER"] = "mock"
os.environ["IMAGE_PROVIDER"] = "mock"
os.environ["FFMPEG_BINARY"] = "ffmpeg"
os.environ["FFPROBE_BINARY"] = "ffprobe"
os.environ["RAZORPAY_WEBHOOK_SECRET"] = "test-webhook-secret"

try:
    import celery as _celery  # noqa: F401
except ModuleNotFoundError:
    fake = types.ModuleType("celery")
    class _Celery:
        def __init__(self, *args, **kwargs):
            self.conf = types.SimpleNamespace()
        def task(self, *args, **kwargs):
            def deco(fn):
                fn.delay = lambda *a, **k: types.SimpleNamespace(id="test-task")
                return fn
            return deco
    fake.Celery = _Celery
    sys.modules["celery"] = fake


def pytest_sessionfinish(session, exitstatus):
    Path("test_bharatvideo_v03.db").unlink(missing_ok=True)
    import shutil
    shutil.rmtree("test_storage_v03", ignore_errors=True)
