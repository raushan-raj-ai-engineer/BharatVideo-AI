#!/usr/bin/env bash
set -euo pipefail
BASE="${OLLAMA_HOST:-http://localhost:11434}"
MODEL="${OLLAMA_MODEL:-llama3.2}"
echo "[OLLAMA] endpoint=$BASE model=$MODEL"
if ! curl -fsS "$BASE/api/tags" >/tmp/bharatvideo_ollama_tags.json; then
  echo "[OLLAMA] FAIL: Ollama is not reachable. Start it with: open -a Ollama" >&2
  exit 1
fi
if ! grep -q "\"${MODEL}" /tmp/bharatvideo_ollama_tags.json; then
  echo "[OLLAMA] model '$MODEL' not found. Pull with: ollama pull $MODEL" >&2
  exit 2
fi
echo "[OLLAMA] PASS"
