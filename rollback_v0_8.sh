#!/usr/bin/env bash
set -euo pipefail
APP_ROOT="${1:-$HOME/Downloads/bharatvideo_ai_mvp_v0_1}"
ENGINE_ROOT="${2:-/Users/maa/agentic-content-factory}"
MARKER="$APP_ROOT/.bharatvideo-v08-last-backup"
[[ -f "$MARKER" ]] || { echo "No V0.8 backup marker: $MARKER" >&2; exit 1; }
BACKUP_ROOT="$(cat "$MARKER")"
[[ -f "$BACKUP_ROOT/app_code.tgz" ]] || { echo "Backup missing: $BACKUP_ROOT" >&2; exit 1; }

echo "[V0.8 ROLLBACK] restoring from $BACKUP_ROOT"
tar -xzf "$BACKUP_ROOT/app_code.tgz" -C "$APP_ROOT"
cp "$BACKUP_ROOT/engine/audio.py" "$ENGINE_ROOT/src/content_factory/cartoon/blender_full/audio.py"
cp "$BACKUP_ROOT/engine/pipeline.py" "$ENGINE_ROOT/src/content_factory/cartoon/blender_full/pipeline.py"
cp "$BACKUP_ROOT/engine/worker_full.py" "$ENGINE_ROOT/src/content_factory/cartoon/blender_full/worker_full.py"
rm -f "$ENGINE_ROOT/tests/test_v68_adaptive_continuity.py"
echo "[V0.8 ROLLBACK] restored app code + audio/pipeline/worker engine files"
echo "Restart Docker containers and engine bridge."
