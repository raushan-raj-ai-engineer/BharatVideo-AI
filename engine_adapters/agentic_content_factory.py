from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass


@dataclass(slots=True)
class EngineResult:
    payload: dict


class AgenticContentFactoryAdapter:
    """Standalone compatibility client for the guarded v0.2 host bridge."""

    def __init__(self, bridge_url: str = "http://localhost:8090", token: str = "change-me-local-dev-token"):
        self.bridge_url = bridge_url.rstrip("/")
        self.token = token

    def _request(self, path: str, method: str = "GET", body: dict | None = None) -> dict:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(
            f"{self.bridge_url}{path}",
            data=data,
            method=method,
            headers={
                "Content-Type": "application/json",
                "X-BharatVideo-Bridge-Token": self.token,
            },
        )
        with urllib.request.urlopen(req, timeout=180) as response:
            return json.loads(response.read().decode("utf-8"))

    def healthcheck(self) -> dict:
        return self._request("/health")

    def preflight(self) -> dict:
        return self._request("/preflight", "POST", {"check": True})

    def generate(self, request: dict) -> EngineResult:
        return EngineResult(self._request("/render", "POST", request))
