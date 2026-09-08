#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi
REPO="${HOST_AGENTIC_CONTENT_FACTORY_ROOT:-/Users/maa/agentic-content-factory}"
TOKEN="${ENGINE_BRIDGE_TOKEN:-change-me-local-dev-token}"
ENGINE_PY="$REPO/.venv/bin/python"
[[ -x "$ENGINE_PY" ]] || ENGINE_PY="$(command -v python3)"
export CONTENT_FACTORY_TTS_CMD="$ENGINE_PY $REPO/scripts/bharatvideo_neural_tts.py --text-file {text_file} --output {output} --character {character}"
exec python3 "$ROOT/engine_bridge/bridge_server.py" --repo "$REPO" --token "$TOKEN" --host 0.0.0.0 --port 8090
