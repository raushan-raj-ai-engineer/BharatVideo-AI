from __future__ import annotations

import httpx

from app.core.config import get_settings


class EngineBridgeError(RuntimeError):
    pass


class EngineBridgeClient:
    def __init__(self):
        settings = get_settings()
        self.url = settings.engine_bridge_url.rstrip("/")
        self.token = settings.engine_bridge_token

    @property
    def headers(self) -> dict[str, str]:
        return {"X-BharatVideo-Bridge-Token": self.token}

    def health(self) -> dict:
        try:
            response = httpx.get(f"{self.url}/health", headers=self.headers, timeout=10.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise EngineBridgeError(f"Engine bridge unavailable: {exc}") from exc

    def preflight(self) -> dict:
        try:
            response = httpx.post(f"{self.url}/preflight", headers=self.headers, json={"check": True}, timeout=180.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise EngineBridgeError(f"Engine preflight failed: {exc}") from exc

    def render(self, *, plan: dict, quality: str = "draft", max_scenes: int | None = 3) -> dict:
        body = {"plan": plan, "quality": quality, "max_scenes": max_scenes, "fresh": True}
        try:
            response = httpx.post(
                f"{self.url}/render", headers=self.headers, json=body, timeout=None
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            detail = ""
            try:
                payload = exc.response.json()
                detail = payload.get("error") or payload.get("stderr") or payload.get("stdout") or str(payload)
            except Exception:
                detail = exc.response.text
            detail = (detail or "").strip()
            if len(detail) > 8000:
                detail = detail[-8000:]
            suffix = f" | renderer detail: {detail}" if detail else ""
            raise EngineBridgeError(
                f"Engine render failed with HTTP {exc.response.status_code}: {exc}{suffix}"
            ) from exc
        except httpx.HTTPError as exc:
            raise EngineBridgeError(f"Engine render transport failed: {exc}") from exc


    def tts(self, *, text: str, voice: str = "Lekha", rate: int = 185) -> dict:
        body = {"text": text, "voice": voice, "rate": rate}
        try:
            response = httpx.post(
                f"{self.url}/tts", headers=self.headers, json=body, timeout=180.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise EngineBridgeError(f"Host TTS failed: {exc}") from exc

    def download_asset(self, asset_id: str) -> bytes:
        try:
            response = httpx.get(
                f"{self.url}/assets/{asset_id}", headers=self.headers, timeout=120.0
            )
            response.raise_for_status()
            return response.content
        except httpx.HTTPError as exc:
            raise EngineBridgeError(f"Could not download engine asset: {exc}") from exc
