.PHONY: run livekit-backend livekit-worker livekit-frontend seed-demo-operator test test-coverage frontend-check ci-check lint compile migration-check format typecheck check clean

run:
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

livekit-backend:
	uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

livekit-worker:
	uv run python -m src.voice_agent.server dev --log-level INFO

livekit-frontend:
	cd src/frontend && npm run dev

seed-demo-operator:
	uv run python -m scripts.seed_demo_operator

test:
	pytest tests/ -v

test-coverage:
	uv run pytest -q --cov=src --cov-report=term-missing --cov-report=xml:coverage.xml --cov-fail-under=60

frontend-check:
	cd src/frontend && npm run lint && npm run test && npm run build

ci-check: lint compile migration-check test-coverage frontend-check

lint:
	uv run ruff check src tests scripts eval_cases

compile:
	uv run python -m compileall -q src tests scripts eval_cases

migration-check:
	APP_ENV=test DATABASE_URL=sqlite:///./data/ci.db uv run python -m alembic heads

format:
	ruff format src/ tests/

typecheck:
	mypy src/

check: lint format test

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
