.PHONY: backend frontend test lint

backend:
	cd backend && uv sync && uv run uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && ([ -d node_modules ] || npm install) && npm run dev

test:
	cd backend && uv run pytest
	cd frontend && npm test

lint:
	cd backend && uv run ruff check .
	cd frontend && npm run build
