# The rig. Standalone: it shares nothing with backend/ but the wire protocol.

.PHONY: help install serve test lint mutants

help:
	@echo "install  install dependencies"
	@echo "serve    run the rig on :8100"
	@echo "test     run the tests"
	@echo "lint     ruff + mypy"
	@echo "mutants  mutation score, against the floor it may not fall below"

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

# 2,488 mutants. Full sweep rather than changed-file scoping: at this size the
# whole thing is affordable, and a partial sweep cannot tell a score that
# improved from one that was never measured. Wall clock depends entirely on
# worker count -- 13 minutes at `--max-children 4`, well under half that on a
# machine left to use all its cores.
mutants:
	uv run mutmut run || true
	uv run mutmut export-cicd-stats
	uv run python scripts/mutation_floor.py
