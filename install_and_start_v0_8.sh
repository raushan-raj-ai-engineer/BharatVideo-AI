#!/usr/bin/env bash
set -Eeuo pipefail
RELEASE_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_ROOT="${1:-$HOME/Downloads/bharatvideo_ai_mvp_v0_1}"
ENGINE_ROOT="${2:-/Users/maa/agentic-content-factory}"

"$RELEASE_DIR/install_v0_8.sh" "$APP_ROOT" "$ENGINE_ROOT"

cd "$APP_ROOT"
if ! docker info >/dev/null 2>&1; then
  echo "[V0.8 START] Docker daemon is not ready; starting Docker Desktop..."
  open -a Docker >/dev/null 2>&1 || true
  for _ in $(seq 1 45); do docker info >/dev/null 2>&1 && break; sleep 2; done
fi
docker info >/dev/null 2>&1 || { echo "[V0.8 START] Docker daemon unavailable" >&2; exit 1; }
echo "[V0.8 START] Recreating Docker services (volumes preserved)..."
docker compose down
docker compose up -d --build --force-recreate

echo "[V0.8 START] Restarting host bridge..."
if command -v lsof >/dev/null 2>&1; then
  PIDS="$(lsof -ti tcp:8090 2>/dev/null || true)"
  if [[ -n "$PIDS" ]]; then kill $PIDS 2>/dev/null || true; sleep 1; fi
fi
mkdir -p logs
nohup ./scripts/start_engine_bridge.sh > logs/engine_bridge_v0_8.log 2>&1 &
BRIDGE_PID=$!
echo "$BRIDGE_PID" > .engine_bridge.pid

# Wait for the authenticated bridge health endpoint using local env token.
TOKEN="$(awk -F= '/^ENGINE_BRIDGE_TOKEN=/{sub(/^ENGINE_BRIDGE_TOKEN=/,""); print; exit}' .env 2>/dev/null || true)"
TOKEN="${TOKEN:-change-me-local-dev-token}"
for _ in $(seq 1 20); do
  if curl -fsS -H "X-BharatVideo-Bridge-Token: $TOKEN" http://127.0.0.1:8090/health > /tmp/bharatvideo_v07_health.json 2>/dev/null; then break; fi
  sleep 1
done
python3 - <<'PY'
import json
from pathlib import Path
p=Path('/tmp/bharatvideo_v07_health.json')
if not p.exists(): raise SystemExit('[V0.8 START] bridge health did not become ready')
d=json.loads(p.read_text())
print('[V0.8 START] bridge health:', json.dumps(d, ensure_ascii=False))
assert d.get('bridge_version') == '0.8.0', d
assert d.get('engine_patch',{}).get('active') is True, d
PY

echo "[V0.8 START] Docker status:"
docker compose ps
echo "[V0.8 START] READY -> http://localhost:3000"
echo "[V0.8 START] Bridge log -> $APP_ROOT/logs/engine_bridge_v0_8.log"
HOST_AGENTIC_CONTENT_FACTORY_ROOT="$ENGINE_ROOT" ./scripts/verify_v0_8.sh
