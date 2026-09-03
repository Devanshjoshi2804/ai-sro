# The rig. Standalone: it shares nothing with backend/ but the wire protocol.

.PHONY: help install serve test lint

help:
	@echo "install  install dependencies"
	@echo "serve    run the rig on :8100"
	@echo "test     run the tests"
	@echo "lint     ruff + mypy"

install:
	uv sync --all-extras

serve:
	uv run uvicorn rig.api:app --reload --port 8100

test:
	uv run pytest -q

lint:
	uv run ruff check src tests
	uv run ruff format --check src tests
	uv run mypy src
