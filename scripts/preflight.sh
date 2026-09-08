#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "BharatVideo AI v0.3 preflight"
command -v docker >/dev/null && echo "docker=PASS" || { echo "docker=MISSING"; exit 1; }
docker compose version >/dev/null && echo "docker_compose=PASS" || { echo "docker_compose=MISSING"; exit 1; }
command -v curl >/dev/null && echo "curl=PASS" || { echo "curl=MISSING"; exit 1; }
command -v say >/dev/null && echo "mac_say=PASS" || echo "mac_say=CHECK (host_say TTS needs macOS say)"
[[ -f "$ROOT/.env" ]] && echo ".env=PASS" || echo ".env=MISSING (copy .env.example)"
[[ -d "${HOST_AGENTIC_CONTENT_FACTORY_ROOT:-/Users/maa/agentic-content-factory}" ]] && echo "agentic_content_factory=PASS" || echo "agentic_content_factory=CHECK_PATH"
if curl -fsS http://localhost:11434/api/tags >/dev/null 2>&1; then echo "ollama=PASS"; else echo "ollama=NOT_RUNNING (LLM fallback can still work)"; fi
echo "preflight=PASS"
