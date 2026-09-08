#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${1:-}"
if [[ -z "$PROJECT_ID" ]]; then
  echo "Usage: $0 <project_id>"
  echo "Find it in the browser project URL or GET http://localhost:8000/v1/projects"
  exit 2
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:8000}"
# NEXT_PUBLIC_API_URL may be browser-only/localhost already. Keep a safe local default.
[[ "$API_URL" == *"host.docker.internal"* ]] && API_URL="http://localhost:8000"
BRIDGE_URL="http://localhost:8090"
TOKEN="${ENGINE_BRIDGE_TOKEN:-change-me-local-dev-token}"
TMP="$(mktemp -d /tmp/bharatvideo_diag.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT

echo "[1/4] Bridge health"
curl -fsS -H "X-BharatVideo-Bridge-Token: $TOKEN" "$BRIDGE_URL/health" | python3 -m json.tool

echo "[2/4] Renderer preflight"
curl -fsS -X POST -H "Content-Type: application/json" \
  -H "X-BharatVideo-Bridge-Token: $TOKEN" \
  -d '{"check":true}' "$BRIDGE_URL/preflight" | python3 -m json.tool

echo "[3/4] Export engine plan for project=$PROJECT_ID"
curl -fsS "$API_URL/v1/projects/$PROJECT_ID/engine-plan" > "$TMP/plan.json"
python3 - "$TMP/plan.json" "$TMP/request.json" <<'PY'
import json, sys
plan=json.load(open(sys.argv[1], encoding='utf-8'))
print(f"plan scenes={len(plan.get('scenes') or [])} characters={plan.get('characters')}")
json.dump({"plan":plan,"quality":"draft","max_scenes":1,"fresh":True}, open(sys.argv[2],'w',encoding='utf-8'), ensure_ascii=False)
PY

echo "[4/4] One-scene draft render (response below contains exact failure stage/stdout/stderr)"
HTTP_CODE=$(curl -sS -o "$TMP/response.json" -w '%{http_code}' -X POST \
  -H "Content-Type: application/json" \
  -H "X-BharatVideo-Bridge-Token: $TOKEN" \
  --data-binary "@$TMP/request.json" "$BRIDGE_URL/render" || true)
echo "HTTP $HTTP_CODE"
python3 -m json.tool "$TMP/response.json" || cat "$TMP/response.json"
[[ "$HTTP_CODE" == "200" ]]
