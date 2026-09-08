#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
[ -f .env ] || cp .env.example .env
cat <<'TXT'
BharatVideo AI MVP bootstrap
1. Ensure Docker Desktop is installed and running.
2. Review .env, especially HOST_AGENTIC_CONTENT_FACTORY_ROOT.
3. Start with: docker compose up --build
TXT
./scripts/preflight.sh
