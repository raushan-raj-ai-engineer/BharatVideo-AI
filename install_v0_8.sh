#!/usr/bin/env bash
set -Eeuo pipefail

RELEASE_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_ROOT="${1:-$HOME/Downloads/bharatvideo_ai_mvp_v0_1}"
ENGINE_ROOT="${2:-/Users/maa/agentic-content-factory}"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_ROOT="$APP_ROOT/.bharatvideo-backups/v0_8_$STAMP"
ENGINE_DIR="$ENGINE_ROOT/src/content_factory/cartoon/blender_full"
AUDIO_SRC="$RELEASE_DIR/engine_patch/src/content_factory/cartoon/blender_full/audio.py"
PIPE_SRC="$RELEASE_DIR/engine_patch/src/content_factory/cartoon/blender_full/pipeline.py"
AUDIO_DST="$ENGINE_DIR/audio.py"
PIPE_DST="$ENGINE_DIR/pipeline.py"
WORKER_SRC="$RELEASE_DIR/engine_patch/src/content_factory/cartoon/blender_full/worker_full.py"
WORKER_DST="$ENGINE_DIR/worker_full.py"
TEST_DST="$ENGINE_ROOT/tests/test_v66_duration_autogrow.py"
CONTINUITY_TEST_DST="$ENGINE_ROOT/tests/test_v68_adaptive_continuity.py"
NEURAL_SRC="$RELEASE_DIR/engine_patch/scripts/bharatvideo_neural_tts.py"
NEURAL_DST="$ENGINE_ROOT/scripts/bharatvideo_neural_tts.py"
COMMITTED=0

fail(){ echo "[V0.8 INSTALL] ERROR: $*" >&2; exit 1; }
sha(){ shasum -a 256 "$1" | awk '{print $1}'; }

rollback_on_error(){
  code=$?
  if [[ $code -ne 0 && $COMMITTED -eq 0 ]]; then
    echo "[V0.8 INSTALL] validation failed; transactional rollback starting..." >&2
    if [[ -f "$BACKUP_ROOT/engine/audio.py" ]]; then cp "$BACKUP_ROOT/engine/audio.py" "$AUDIO_DST"; fi
    if [[ -f "$BACKUP_ROOT/engine/pipeline.py" ]]; then cp "$BACKUP_ROOT/engine/pipeline.py" "$PIPE_DST"; fi
    if [[ -f "$BACKUP_ROOT/engine/worker_full.py" ]]; then cp "$BACKUP_ROOT/engine/worker_full.py" "$WORKER_DST"; fi
    if [[ -f "$BACKUP_ROOT/app_code.tgz" ]]; then
      # Remove release-controlled app code only, then restore old code. Runtime data and .env remain untouched.
      rsync -a --delete --exclude='.git/' --exclude='.env' --exclude='storage/' --exclude='.bharatvideo-backups/' --exclude='apps/web/node_modules/' --exclude='apps/web/.next/' "$BACKUP_ROOT/empty/" "$APP_ROOT/" 2>/dev/null || true
      tar -xzf "$BACKUP_ROOT/app_code.tgz" -C "$APP_ROOT" || true
    fi
    echo "[V0.8 INSTALL] rollback complete." >&2
  fi
  exit $code
}
trap rollback_on_error ERR

[[ -d "$APP_ROOT" ]] || fail "App root not found: $APP_ROOT"
[[ -d "$ENGINE_DIR" ]] || fail "Engine root not compatible: $ENGINE_ROOT"
[[ -f "$AUDIO_SRC" && -f "$PIPE_SRC" && -f "$WORKER_SRC" ]] || fail "V6.8 engine patch missing"
[[ -f "$RELEASE_DIR/apps/api/app/main.py" ]] || fail "Release app files missing"
mkdir -p "$BACKUP_ROOT/engine" "$BACKUP_ROOT/empty"

echo "[V0.8 INSTALL] backup=$BACKUP_ROOT"
(
  cd "$APP_ROOT"
  tar --exclude='./.git' --exclude='./.env' --exclude='./storage' --exclude='./apps/web/node_modules' --exclude='./apps/web/.next' --exclude='./.bharatvideo-backups' -czf "$BACKUP_ROOT/app_code.tgz" .
)
cp "$AUDIO_DST" "$BACKUP_ROOT/engine/audio.py"
cp "$PIPE_DST" "$BACKUP_ROOT/engine/pipeline.py"
cp "$WORKER_DST" "$BACKUP_ROOT/engine/worker_full.py"

# Overlay application, preserving environment/runtime data.
rsync -a --delete \
  --exclude='.git/' --exclude='.env' --exclude='storage/' --exclude='apps/web/node_modules/' --exclude='apps/web/.next/' \
  --exclude='engine_patch/' --exclude='.bharatvideo-backups/' \
  "$RELEASE_DIR/" "$APP_ROOT/"

# Force exact tested engine files into the exact path seen in the user's traceback.
install -m 0644 "$AUDIO_SRC" "$AUDIO_DST"
install -m 0644 "$PIPE_SRC" "$PIPE_DST"
install -m 0644 "$WORKER_SRC" "$WORKER_DST"
install -m 0644 "$RELEASE_DIR/engine_patch/tests/test_v66_duration_autogrow.py" "$TEST_DST"
install -m 0644 "$RELEASE_DIR/engine_patch/tests/test_v68_adaptive_continuity.py" "$CONTINUITY_TEST_DST"
mkdir -p "$ENGINE_ROOT/scripts"
install -m 0755 "$NEURAL_SRC" "$NEURAL_DST"

# 1) Byte-for-byte verification. A false "installed" state is impossible past this point.
[[ "$(sha "$AUDIO_SRC")" == "$(sha "$AUDIO_DST")" ]] || fail "audio.py checksum mismatch after copy"
[[ "$(sha "$PIPE_SRC")" == "$(sha "$PIPE_DST")" ]] || fail "pipeline.py checksum mismatch after copy"
[[ "$(sha "$WORKER_SRC")" == "$(sha "$WORKER_DST")" ]] || fail "worker_full.py checksum mismatch after copy"
grep -q 'ADAPTIVE AUDIO CONTINUITY V6.8' "$AUDIO_DST" || fail "V6.8 audio marker absent from ACTIVE file"
grep -q 'ADAPTIVE SCENE STITCH V6.8' "$PIPE_DST" || fail "V6.8 pipeline marker absent from ACTIVE file"
grep -q 'BHARATVIDEO PERFORMANCE V6.8' "$WORKER_DST" || fail "V6.8 performance marker absent from ACTIVE worker"
grep -q 'CONTENT_FACTORY_TTS_CMD' "$AUDIO_DST" || fail "neural TTS hook absent from active audio.py"

PY=""
for candidate in "$ENGINE_ROOT/.venv/bin/python" "$ENGINE_ROOT/venv/bin/python" "$(command -v python3 || true)"; do
  if [[ -n "$candidate" && -x "$candidate" ]]; then PY="$candidate"; break; fi
done
[[ -n "$PY" ]] || fail "No Python found"

if "$PY" -c "import edge_tts" >/dev/null 2>&1; then
  echo "[V0.8 INSTALL] Neural Hindi TTS already installed; keeping existing runtime."
  "$PY" -c "import edge_tts; print('[V0.8 VERIFY] edge_tts import PASS')"
elif [[ "${BHARATVIDEO_SKIP_TTS_INSTALL:-0}" == "1" ]]; then
  echo "[V0.8 INSTALL] CI simulation: edge-tts installation explicitly skipped."
else
  echo "[V0.8 INSTALL] Installing neural Hindi TTS runtime..."
  "$PY" -m pip install -q "edge-tts==7.2.8" || fail "edge-tts install failed; internet access is required once for neural TTS"
  "$PY" -c "import edge_tts; print('[V0.8 VERIFY] edge_tts import PASS')"
fi

"$PY" -m py_compile "$AUDIO_DST" "$PIPE_DST" "$WORKER_DST" "$NEURAL_DST" "$APP_ROOT/engine_bridge/bridge_server.py"

# 2) Import-path verification: prove Python imports the exact active file from traceback path.
EXPECTED_AUDIO="$AUDIO_DST" EXPECTED_PIPE="$PIPE_DST" PYTHONPATH="$ENGINE_ROOT/src" "$PY" - <<'PY'
import os
from pathlib import Path
import content_factory.cartoon.blender_full.audio as audio
import content_factory.cartoon.blender_full.pipeline as pipeline
actual_audio=Path(audio.__file__).resolve(); actual_pipe=Path(pipeline.__file__).resolve()
expected_audio=Path(os.environ['EXPECTED_AUDIO']).resolve(); expected_pipe=Path(os.environ['EXPECTED_PIPE']).resolve()
print(f"[V0.8 VERIFY] imported audio={actual_audio}")
print(f"[V0.8 VERIFY] imported pipeline={actual_pipe}")
assert actual_audio == expected_audio, (actual_audio, expected_audio)
assert actual_pipe == expected_pipe, (actual_pipe, expected_pipe)
assert 'ADAPTIVE AUDIO CONTINUITY V6.8' in expected_audio.read_text(encoding='utf-8')
assert 'ADAPTIVE SCENE STITCH V6.8' in expected_pipe.read_text(encoding='utf-8')
PY

# 3) Exact regression test, including the reported 3.59s voice / 3.00s scene failure.
(
  cd "$ENGINE_ROOT"
  PYTHONPATH="$ENGINE_ROOT/src" "$PY" -m pytest -q tests/test_v66_duration_autogrow.py tests/test_v68_adaptive_continuity.py
)

# 4) App code sanity.
if [[ -x "$APP_ROOT/.venv/bin/python" ]]; then APP_PY="$APP_ROOT/.venv/bin/python"; else APP_PY="$PY"; fi
"$APP_PY" -m py_compile "$APP_ROOT/apps/api/app/main.py" "$APP_ROOT/apps/api/app/api/billing.py" "$APP_ROOT/apps/api/app/services/billing.py" "$APP_ROOT/apps/api/app/models/account.py" "$APP_ROOT/engine_bridge/bridge_server.py"
bash -n "$APP_ROOT/scripts/start_engine_bridge.sh"

# Add new V0.8 payment config keys without overwriting existing user values.
if [[ -f "$APP_ROOT/.env" ]]; then
  grep -q '^RAZORPAY_WEBHOOK_SECRET=' "$APP_ROOT/.env" || printf '\nRAZORPAY_WEBHOOK_SECRET=\n' >> "$APP_ROOT/.env"
  grep -q '^RAZORPAY_EXPECTED_ACCOUNT_ID=' "$APP_ROOT/.env" || printf 'RAZORPAY_EXPECTED_ACCOUNT_ID=\n' >> "$APP_ROOT/.env"
fi

printf '%s\n' "$BACKUP_ROOT" > "$APP_ROOT/.bharatvideo-v08-last-backup"
printf '%s\n' "$(sha "$AUDIO_DST")" > "$APP_ROOT/.bharatvideo-v08-audio-sha256"
printf '%s\n' "$(sha "$PIPE_DST")" > "$APP_ROOT/.bharatvideo-v08-pipeline-sha256"
printf '%s\n' "$(sha "$WORKER_DST")" > "$APP_ROOT/.bharatvideo-v08-worker-sha256"
COMMITTED=1
trap - ERR

echo "[V0.8 INSTALL] ================================================"
echo "[V0.8 INSTALL] APP OVERLAY                     PASS"
echo "[V0.8 INSTALL] ACTIVE ENGINE BYTE CHECK         PASS"
echo "[V0.8 INSTALL] ACTIVE PYTHON IMPORT PATH        PASS"
echo "[V0.8 INSTALL] DURATION + CONTINUITY REGRESSION  PASS"
echo "[V0.8 INSTALL] RENDERER                         V6.8"
echo "[V0.8 INSTALL] BRIDGE                           0.8.0"
echo "[V0.8 INSTALL] PAYMENT HARDENING                RAZORPAY WEBHOOK + IDEMPOTENCY"
echo "[V0.8 INSTALL] .env + Docker volumes            PRESERVED"
echo "[V0.8 INSTALL] backup=$BACKUP_ROOT"
echo "[V0.8 INSTALL] ================================================"
