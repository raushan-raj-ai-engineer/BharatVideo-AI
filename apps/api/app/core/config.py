from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite:///./bharatvideo.db"
    redis_url: str = "redis://localhost:6379/0"
    storage_backend: str = "local"
    local_storage_dir: str = "./storage"
    public_asset_base_url: str = "http://localhost:8000/assets"
    cors_origins: str = "http://localhost:3000"

    # Story / scene planning. Ollama keeps local development API-cost free.
    llm_provider: str = "ollama"  # ollama | mock
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "llama3.2"
    llm_timeout_seconds: float = 120.0
    llm_temperature: float = 0.7
    llm_fallback_to_mock: bool = True

    # Existing Agentic Content Factory is executed by a guarded host bridge.
    engine_mode: str = "bridge"  # bridge | disabled
    engine_bridge_url: str = "http://host.docker.internal:8090"
    engine_bridge_token: str = "change-me-local-dev-token"
    agentic_content_factory_root: str = "/workspace/agentic-content-factory"

    # media pipeline. Local defaults keep development API-cost free.
    tts_provider: str = "host_say"  # host_say | mock
    tts_voice: str = "Lekha"
    tts_speech_rate: int = 185
    image_provider: str = "mock"  # draft storyboard only; REAL video uses Blender bridge
    ffmpeg_binary: str = "ffmpeg"
    ffprobe_binary: str = "ffprobe"

    # v0.7 authentication / pricing. Change AUTH_SECRET before public deployment.
    auth_secret: str = "dev-change-this-auth-secret"
    auth_token_hours: int = 168
    signup_credits: int = 30
    billing_mode: str = "mock"  # mock | razorpay
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""
    razorpay_expected_account_id: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
