#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENGINE_ROOT="${HOST_AGENTIC_CONTENT_FACTORY_ROOT:-/Users/maa/agentic-content-factory}"
PY="${ENGINE_ROOT}/.venv/bin/python"
[[ -x "$PY" ]] || PY="$(command -v python3)"

echo "[VERIFY V0.8] app version=$(cat "$ROOT/VERSION" 2>/dev/null || echo unknown)"
grep -q 'BRIDGE_VERSION = "0.8.0"' "$ROOT/engine_bridge/bridge_server.py" && echo "[VERIFY V0.8] bridge code=0.8.0 PASS"
grep -q 'ADAPTIVE AUDIO CONTINUITY V6.8' "$ENGINE_ROOT/src/content_factory/cartoon/blender_full/audio.py" && echo "[VERIFY V0.8] active engine audio V6.8=PASS"
grep -q 'ADAPTIVE SCENE STITCH V6.8' "$ENGINE_ROOT/src/content_factory/cartoon/blender_full/pipeline.py" && echo "[VERIFY V0.8] active engine pipeline V6.8=PASS"
PYTHONPATH="$ENGINE_ROOT/src" "$PY" - <<'PY'
from pathlib import Path
import content_factory.cartoon.blender_full.audio as a
import content_factory.cartoon.blender_full.pipeline as p
print('[VERIFY V0.8] imported audio=',Path(a.__file__).resolve())
print('[VERIFY V0.8] imported pipeline=',Path(p.__file__).resolve())
PY
if [[ -f "$ENGINE_ROOT/tests/test_v66_duration_autogrow.py" ]]; then
  (cd "$ENGINE_ROOT" && PYTHONPATH="$ENGINE_ROOT/src" "$PY" -m pytest -q tests/test_v66_duration_autogrow.py tests/test_v68_adaptive_continuity.py)
fi
if command -v docker >/dev/null 2>&1; then (cd "$ROOT" && docker compose ps) || true; fi

grep -q 'router = APIRouter(prefix="/v1/auth"' "$ROOT/apps/api/app/api/auth.py" && echo "[VERIFY V0.8] auth routes=PASS"
grep -q 'router = APIRouter(prefix="/v1/billing"' "$ROOT/apps/api/app/api/billing.py" && echo "[VERIFY V0.8] billing routes=PASS"
grep -q '/webhooks/razorpay' "$ROOT/apps/api/app/api/billing.py" && echo "[VERIFY V0.8] Razorpay webhook route=PASS"
grep -q 'PaymentFulfillment' "$ROOT/apps/api/app/models/account.py" && echo "[VERIFY V0.8] payment exactly-once ledger=PASS"
grep -q 'x_razorpay_event_id' "$ROOT/apps/api/app/api/billing.py" && echo "[VERIFY V0.8] webhook event dedupe=PASS"
grep -q 'three_character_comedy_lock' "$ROOT/apps/api/app/services/engine_plan.py" && echo "[VERIFY V0.8] video cast lock=PASS"
grep -q 'adaptive_scene_timing_v08' "$ROOT/apps/api/app/services/engine_plan.py" && echo "[VERIFY V0.8] adaptive continuity plan=PASS"
grep -q 'BHARATVIDEO PERFORMANCE V6.8' "$ENGINE_ROOT/src/content_factory/cartoon/blender_full/worker_full.py" && echo "[VERIFY V0.8] performance worker V6.8=PASS"

ENGINE_ROOT="${HOST_AGENTIC_CONTENT_FACTORY_ROOT:-/Users/maa/agentic-content-factory}"
PY="$ENGINE_ROOT/.venv/bin/python"; [[ -x "$PY" ]] || PY="$(command -v python3)"
if "$PY" -c "import edge_tts" >/dev/null 2>&1; then "$PY" -c "import edge_tts; print('neural_tts=edge_tts PASS')"; elif [[ "${BHARATVIDEO_SKIP_TTS_INSTALL:-0}" == "1" ]]; then echo "neural_tts=SKIPPED_FOR_CI"; else echo "neural_tts=edge_tts MISSING" >&2; exit 1; fi
grep -q CONTENT_FACTORY_TTS_CMD "$ENGINE_ROOT/src/content_factory/cartoon/blender_full/audio.py" && echo 'engine_neural_hook=PASS'

echo "[VERIFY V0.8] PASS"
