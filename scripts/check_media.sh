#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi
printf 'BharatVideo AI v0.3 media check\n'
command -v docker >/dev/null && echo 'docker=PASS' || { echo 'docker=MISSING'; exit 1; }
command -v ffmpeg >/dev/null && echo 'host_ffmpeg=PASS' || echo 'host_ffmpeg=CHECK (Docker image has its own ffmpeg)'
command -v say >/dev/null && echo 'mac_say=PASS' || echo 'mac_say=MISSING (set TTS_PROVIDER=mock if not on macOS)'
if curl -fsS -H "X-BharatVideo-Bridge-Token: ${ENGINE_BRIDGE_TOKEN:-change-me-local-dev-token}" http://localhost:8090/health >/dev/null 2>&1; then
  echo 'engine_bridge=PASS'
else
  echo 'engine_bridge=NOT_RUNNING (required for host_say TTS and Blender)'
fi
if curl -fsS http://localhost:8000/health >/dev/null 2>&1; then
  echo 'api=PASS'
else
  echo 'api=NOT_RUNNING'
fi
echo 'media_check=PASS'
