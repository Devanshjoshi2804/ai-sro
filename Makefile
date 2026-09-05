# AI-SRO — top-level task runner.
#
# Every command a developer needs on day one lives here. If you find yourself
# typing a long command twice, it belongs in this file.

COMPOSE := docker compose -f infra/docker-compose.yml
BACKEND := cd backend &&
FRONTEND := cd frontend &&

.DEFAULT_GOAL := help
.PHONY: help up down ps logs reset install migrate revision api worker status web vault-key \
        lint lint-backend lint-frontend format test test-unit test-integration \
        test-contract test-browser types check ingest-kb seed-skills gen-recorder \
        mutants-backend

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
	$(BACKEND) uv run mypy src tests/unit/fakes.py
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

test-browser: ## Drive a real Chrome with the extension loaded
	$(BACKEND) uv run pytest tests/browser -q

fixtures: ## Recapture the extension's golden payloads from a real session
	$(BACKEND) uv run python -m tests.browser.capture_fixtures

test-frontend: ## The console's own tests
	$(FRONTEND) npm test

mutants-backend: ## Mutation score for the skill application package, against its floor
	$(BACKEND) uv run mutmut run || true
	$(BACKEND) uv run mutmut export-cicd-stats
	$(BACKEND) uv run python scripts/mutation_floor.py

test-extension: ## The extension's own self-checks, in plain node
	node new-chrome-extension/src/background/queue.test.mjs
	node new-chrome-extension/src/background/queue.upgrade.test.mjs
	node new-chrome-extension/src/background/showing.test.mjs
	node new-chrome-extension/src/background/frames.test.mjs
	node new-chrome-extension/src/background/pages.test.mjs
	node new-chrome-extension/src/background/finishing.test.mjs
	node new-chrome-extension/src/background/watching-across-a-reload.test.mjs
	node new-chrome-extension/src/background/trees.test.mjs
	node new-chrome-extension/src/background/mirror.test.mjs
	node new-chrome-extension/src/background/rig-settings.test.mjs
	node new-chrome-extension/src/content/network.test.mjs
	node new-chrome-extension/src/content/sensitivity.test.mjs
	node new-chrome-extension/src/content/watch.test.mjs
	node new-chrome-extension/src/panel/panel.test.mjs
	node new-chrome-extension/src/panel/ledger.test.mjs
	node new-chrome-extension/src/panel/strip.test.mjs
	node new-chrome-extension/src/panel/today.test.mjs
	node new-chrome-extension/src/panel/run-card.test.mjs
	node new-chrome-extension/src/panel/nudge.test.mjs
	node new-chrome-extension/src/tokens.test.mjs

check: lint test test-contract test-frontend test-extension test-browser ## What CI runs
