#!/usr/bin/env bash
set -euo pipefail
SOURCE="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${1:-}"
if [[ -z "$TARGET" ]]; then
  echo "Usage: $0 /path/to/your/current/bharatvideo_project" >&2
  exit 2
fi
TARGET="$(cd "$TARGET" && pwd)"
if [[ "$SOURCE" == "$TARGET" ]]; then
  echo "Run this script from the extracted v0.3 package, not from the target directory." >&2
  exit 4
fi
if [[ ! -f "$TARGET/docker-compose.yml" || ! -d "$TARGET/apps" ]]; then
  echo "Target does not look like an existing BharatVideo install: $TARGET" >&2
  exit 3
fi
BACKUP="$TARGET/.upgrade-backup-v0_2-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP"
for p in apps engine_adapters engine_bridge scripts docker-compose.yml README.md ARCHITECTURE.md ROADMAP.md .env.example VERSION; do
  [[ -e "$TARGET/$p" ]] && cp -R "$TARGET/$p" "$BACKUP/" || true
done
# Preserve .env, .git and Docker named volumes. Overlay application source only.
for p in apps engine_adapters engine_bridge packages scripts docker-compose.yml README.md ARCHITECTURE.md ROADMAP.md .env.example Makefile .gitignore VERSION; do
  rm -rf "$TARGET/$p"
  cp -R "$SOURCE/$p" "$TARGET/$p"
done
ENVFILE="$TARGET/.env"
if [[ -f "$ENVFILE" ]]; then
  add_env(){ local key="$1" value="$2"; grep -q "^${key}=" "$ENVFILE" || printf '\n%s=%s\n' "$key" "$value" >> "$ENVFILE"; }
  add_env TTS_PROVIDER host_say
  add_env TTS_VOICE Lekha
  add_env TTS_SPEECH_RATE 185
  add_env IMAGE_PROVIDER mock
  add_env FFMPEG_BINARY ffmpeg
  add_env FFPROBE_BINARY ffprobe
fi
echo "[UPGRADE] v0.3 overlay complete: $TARGET"
echo "[UPGRADE] backup: $BACKUP"
echo "[UPGRADE] existing .env, .git history and Docker named volumes were preserved"
echo "[UPGRADE] Base.metadata.create_all will add the new media_assets table on API startup"
