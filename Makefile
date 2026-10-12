.PHONY: dev test api worker web

dev:
	docker compose up --build

test:
	PYTHONPATH=apps/api:. pytest -q

api:
	PYTHONPATH=apps/api uvicorn app.main:app --reload --port 8000

worker:
	PYTHONPATH=apps/api python -m app.workers.render_worker

web:
	cd apps/web && npm run dev
