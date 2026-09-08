from __future__ import annotations

from app.core.config import get_settings


def provider_status() -> dict:
    s = get_settings()
    return {
        "story": {"provider": s.llm_provider, "model": s.ollama_model if s.llm_provider == "ollama" else s.llm_provider, "ready": s.llm_provider != "disabled"},
        "voice": {"provider": s.tts_provider, "ready": s.tts_provider != "disabled"},
        "image": {"provider": s.image_provider, "ready": s.image_provider != "disabled"},
        "video": {"provider": "blender_bridge" if s.engine_mode != "disabled" else "disabled", "ready": s.engine_mode != "disabled", "premium_external": False},
        "external_video": {"provider": "not_configured", "ready": False, "note": "Veo/Runway adapter boundary reserved; no paid calls in v0.7."},
    }
