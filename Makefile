.PHONY: up down test-api api web bridge ollama-check media-check
up:
	docker compose up --build

down:
	docker compose down

test-api:
	cd apps/api && pytest -q

api:
	cd apps/api && uvicorn app.main:app --reload

web:
	cd apps/web && npm run dev

bridge:
	./scripts/start_engine_bridge.sh

ollama-check:
	./scripts/check_ollama.sh

media-check:
	./scripts/check_media.sh
