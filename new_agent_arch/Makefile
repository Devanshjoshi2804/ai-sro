# The rig. Standalone: it shares nothing with backend/ but the wire protocol.

.PHONY: help install serve test lint mutants bakeoff

help:
	@echo "install  install dependencies"
	@echo "serve    run the rig on :8100"
	@echo "test     run the tests"
	@echo "lint     ruff + mypy"
	@echo "mutants  mutation score, against the floor it may not fall below"
	@echo "bakeoff  ask every model the same day of evidence; costs real money"

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

# One day of real evidence past several models, side by side: what each costs,
# how long it takes, and what it finds. Real keys, real money -- which is why
# it is a command and not a button on the page. `--dry` prints the plan and
# spends nothing; `--budget-usd` is the ceiling for the whole sweep.
#
#   make bakeoff                     the default five models, $5 ceiling
#   make bakeoff ARGS="--dry"        what it would ask, and of whom
#   make bakeoff ARGS="--models gemini-3.8-flash,claude-haiku-4-5-20251001"
bakeoff:
	uv run python scripts/bakeoff.py --db $(or $(DB),rig.db) --tenant $(or $(TENANT),new) $(ARGS)
