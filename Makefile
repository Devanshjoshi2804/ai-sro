# AI-SRO — top-level task runner.
#
# Every command a developer needs on day one lives here. If you find yourself
# typing a long command twice, it belongs in this file.

COMPOSE := docker compose -f infra/docker-compose.yml
BACKEND := cd backend &&
FRONTEND := cd frontend &&

.DEFAULT_GOAL := help
.PHONY: help up down ps logs reset install migrate revision api worker status web vault-key one-whole-run \
        lint lint-backend lint-frontend format test test-unit test-integration \
        test-contract test-browser types check ingest-kb seed-skills gen-recorder \
        mutants-backend open-joins two-miners

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# --- infrastructure ---------------------------------------------------------

up: ## Start the local stack (postgres, minio, temporal, steel, otel)
	$(COMPOSE) up -d --wait

down: ## Stop the local stack
	$(COMPOSE) down

ps: ## Service health overview
	$(COMPOSE) ps

logs: ## Tail all service logs
	$(COMPOSE) logs -f

reset: ## Destroy all local data and start clean
	$(COMPOSE) down -v
	$(MAKE) up
	$(MAKE) migrate

# --- backend ----------------------------------------------------------------

install: ## Install backend and frontend dependencies
	$(BACKEND) uv sync --all-extras
	$(FRONTEND) npm ci

vault-key: ## Generate a vault key: export SRO_VAULT_KEY=$$(make -s vault-key)
	@$(BACKEND) uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

migrate: ## Apply database migrations
	$(BACKEND) uv run alembic upgrade head

revision: ## Autogenerate a migration: make revision m="add foo"
	$(BACKEND) uv run alembic revision --autogenerate -m "$(m)"

api: ## Run the API with reload
	$(BACKEND) uv run uvicorn sro.main:app --reload --port 8000

worker: ## Run the Temporal worker
	$(BACKEND) uv run python -m sro.infrastructure.temporal.worker

status: ## Which commit each running process is actually on, beside this checkout
	@$(BACKEND) uv run python scripts/status.py

# --- frontend ---------------------------------------------------------------

panel-shot: ## A picture of the side panel as it looks now: make panel-shot [beside=https://…]
	@token=$$($(BACKEND) uv run python -m sro.cli.mint $(or $(tenant),acme) $(or $(principal),operator) --days 30); \
	  cd backend && SRO_TOKEN=$$token SRO_BESIDE=$(beside) uv run python -u scripts/panel_shot.py

dev-browser: ## A Chromium with the extension loaded and signed in: make dev-browser [tenant=acme principal=you]
	@token=$$($(BACKEND) uv run python -m sro.cli.mint $(or $(tenant),acme) $(or $(principal),operator) --days 30); \
	  cd backend && SRO_TOKEN=$$token uv run python -u scripts/dev_browser.py

web: ## Run the Next.js dev server on :3000
	$(FRONTEND) npm run dev

ingest-kb: ## Load the recorded Blue Yonder knowledge base: make ingest-kb [tenant=acme]
	$(BACKEND) uv run python -m sro.infrastructure.knowledge.ingest $(or $(tenant),acme)

seed-skills: ## Turn recorded flows into skills, no teaching required: make seed-skills [tenant=acme]
	$(BACKEND) uv run python -m sro.infrastructure.knowledge.seed_skills $(or $(tenant),acme)

auth-secret: ## Generate a signing key for this deployment's own credentials
	@python3 -c "import secrets; print('SRO_AUTH_SECRET=' + secrets.token_urlsafe(48))"

token: ## Issue a credential: make token tenant=acme principal=you [days=30]
	@$(BACKEND) uv run python -m sro.cli.mint $(or $(tenant),acme) $(or $(principal),operator) --days $(or $(days),30)

observe: ## Read or change a tenant's observation policy: make observe tenant=acme args="--on"
	@$(BACKEND) uv run python -m sro.cli.observe $(or $(tenant),acme) $(args)

read-gestures: ## Read each named tenant's unread gestures, once: make read-gestures tenants="acme new"
	@$(BACKEND) uv run python -m sro.cli.read_cron $(or $(tenants),acme)

types: ## Regenerate frontend API types from the backend OpenAPI document
	$(BACKEND) uv run python -m sro.interface.http.export_openapi > ../frontend/openapi.json
	$(FRONTEND) npm run generate:types

gen-recorder: ## Regenerate the extension's copy of the page recorder, secrets baked in
	$(BACKEND) uv run python -m sro.infrastructure.steel.generate_extension_recorder

tokens: ## Copy the brand palette from the console into the extension
	$(BACKEND) uv run python scripts/write_tokens.py

verify-held: ## Prove a person typing in their own browser reaches the console
	@token=$$($(BACKEND) uv run python -m sro.cli.mint $(or $(tenant),acme) $(or $(principal),operator) --days 1); \
	  cd backend && SRO_TOKEN=$$token uv run python -u scripts/verify_held.py

shots: ## Every screen at three widths, for comparing before and after: make shots out=/tmp/before
	@token=$$($(BACKEND) uv run python -m sro.cli.mint $(or $(tenant),acme) $(or $(principal),operator) --days 1); \
	  cd backend && SRO_TOKEN=$$token SRO_SHOTS=$(or $(out),/tmp/sro-shots) uv run python -u scripts/route_shots.py

# --- quality ----------------------------------------------------------------

lint: lint-backend lint-frontend lint-extension ## Run every linter

lint-backend: ## ruff + mypy --strict + import-linter
	$(BACKEND) uv run ruff check .
	$(BACKEND) uv run ruff format --check .
	$(BACKEND) uv run mypy src tests
	$(BACKEND) uv run lint-imports

lint-frontend: ## eslint + tsc
	$(FRONTEND) npm run lint
	$(FRONTEND) npm run typecheck

lint-extension: ## no-undef over the extension, which has no build step to catch it
	cd new-chrome-extension && ../frontend/node_modules/.bin/eslint .

format: ## Autoformat both sides
	$(BACKEND) uv run ruff check --fix .
	$(BACKEND) uv run ruff format .
	$(FRONTEND) npm run format

test: test-unit test-integration ## Unit + integration tests

test-unit: ## Fast tests. No Docker, no network.
	$(BACKEND) uv run pytest tests/unit -q

test-integration: ## Tests against real Postgres/MinIO via testcontainers
	$(BACKEND) uv run pytest tests/integration -q

test-contract: ## Fuzz the API against its own OpenAPI schema
	$(BACKEND) uv run pytest tests/contract -q

one-whole-run: ## A job watched in a real Chrome and then done by the system, end to end
	@# The only thing in this repository that finishes a workflow run. Needs
	@# the API up and a Chromium Playwright can load an extension into; the
	@# tenant is created by the first credential it mints, and its observation
	@# policy has to be on (`make observe tenant=rigproof args=--on`).
	@#
	@# `args="--live --runs 4"` is the whole ladder: three live runs each
	@# stopped for a person to press Approve in the real panel, and a fourth
	@# that nobody is asked about, because by then the job has earned it.
	@#
	@# `args="--via-trigger"` starts each run by firing a trigger that names
	@# the job instead of pressing the run endpoint -- the path a schedule
	@# takes with nobody in the room. Always live, and it still stops for the
	@# panel until the job has earned the right not to.
	@#
	@# `args="--offer"` does the whole job by hand a second time and reads
	@# what the panel says about it: a browser served a shape it has not seen
	@# before, offering the job off its own gestures. The offer lands in the
	@# middle of the doing, because an offer has to leave something to finish.
	$(BACKEND) uv run python scripts/one_whole_run.py $(args)

test-browser: ## Drive a real Chrome with the extension loaded
	$(BACKEND) uv run pytest tests/browser -q

fixtures: ## Recapture the extension's golden payloads from a real session
	$(BACKEND) uv run python -m tests.browser.capture_fixtures

test-frontend: ## The console's own tests
	$(FRONTEND) npm test

# 2,294 mutants over the 2,895-test unit suite, from an empty `mutants/` on a
# machine using all its cores. Most of that is the one-off stats collection;
# the mutant runs themselves are fast, because mutmut runs only the tests that
# cover each one.
mutants-backend: ## Mutation score for the bridge and the ladder, against their floors
	$(BACKEND) uv run mutmut run || true
	$(BACKEND) uv run mutmut export-cicd-stats
	$(BACKEND) uv run python scripts/mutation_floor.py

open-joins: ## The joins waiting on a person -- the last unmet item of phase 7's precondition
	@$(BACKEND) uv run python scripts/open_joins.py $(args)

two-miners: ## Both miners over one tenant, side by side: make two-miners tenant=acme
	@$(BACKEND) uv run python scripts/two_miners.py $(or $(tenant),acme) $(args)

offer-replay: ## Would the offer name the right job? The corpus's gestures through the real matcher, no browser
	cd new_agent_arch && uv run python scripts/dry_run.py --replay /tmp/rig-replay.json > /dev/null && node ../new-chrome-extension/scripts/offer-replay.mjs /tmp/rig-replay.json

# Beside the rig's rather than replacing it: the same measurement from the
# other store, so the two can be read against each other until phase 7 deletes
# the rig and its target with it.
offer-replay-backend: ## The same question of the backend's own store, through the same matcher
	$(BACKEND) uv run python scripts/dry_run.py --replay /tmp/backend-replay.json > /dev/null && node ../new-chrome-extension/scripts/offer-replay.mjs /tmp/backend-replay.json

test-extension: ## The extension's own self-checks, in plain node
	@# Discovered, not listed. This target named all 25 suites by hand until
	@# 2026-09-10, and the list was load-bearing in the wrong direction: phase
	@# 5 deleted `mirror.test.mjs` without editing it, the run aborted at suite
	@# 11 of 25, and the grep watching for failures returned zero -- green. A
	@# file added and forgotten was the same defect facing the other way.
	@#
	@# `**/*.test.?(c|m)js` is one of node's own default patterns and glob
	@# positional arguments have worked since v21; this repo runs v24. It is
	@# the whole tree and not `src/` and `scripts/`, because those two were a
	@# hand-written list again wearing a glob: a suite named `.test.cjs`, or
	@# put in `mock-server/` or `fixtures/`, was skipped in silence. Measured
	@# both ways -- one planted throwing file of each kind: exit 0 under the
	@# two narrow globs, exit 1 under this one. `node_modules` is still not
	@# descended into (measured too, with a throwing file planted in one),
	@# and the extension has none of its own -- eslint comes from the
	@# frontend's.
	@#
	@# Both suite styles survive the move -- 9 files use `node:test`, 17 are
	@# plain scripts that throw -- because the runner spawns one process per
	@# file and reads its exit code. Verified in both directions: 0 when green,
	@# 1 for a `node:test` failure AND 1 for a plain script that throws.
	@#
	@# One process per file also retires two ordering traps the old serial run
	@# had: `commands.js`'s `abort()` poisoned a run id in module scope with no
	@# undo, so the Stop tests had to run last, and `shapesFor`'s five-minute
	@# module-scope cache meant only the first test in the process could pin a
	@# shapes request. Neither survives a fresh process per file.
	cd new-chrome-extension && node --test "**/*.test.?(c|m)js"

check: lint test test-contract test-frontend test-extension test-browser ## What CI runs
