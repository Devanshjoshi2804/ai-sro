# AI-SRO — top-level task runner.
#
# Every command a developer needs on day one lives here. If you find yourself
# typing a long command twice, it belongs in this file.

COMPOSE := docker compose -f infra/docker-compose.yml

# `DOCKER="sudo docker"` on a host where you are not in the `docker` group --
# which is most shared machines, because that group is root by another name.
DOCKER ?= docker
DEPLOY := $(DOCKER) compose -f infra/docker-compose.deploy.yml --env-file $(or $(env),infra/.env.qa)
BACKEND := cd backend &&
FRONTEND := cd frontend &&

.DEFAULT_GOAL := help
.PHONY: help up down ps logs reset install migrate revision api worker status web vault-key one-whole-run \
        lint lint-backend check-code-notes lint-frontend format test test-unit test-integration \
        test-replay record-histories \
        test-contract test-browser types check ingest-kb gen-recorder eval eval-ci eval-redact \
        mutants-backend images smoke gen-deployment migrate-vault-keys \
        steel-up steel-down steel-env

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

steel-up: ## This worktree's own Steel; its URLs go to .env.steel, which the tests load
	$(BACKEND) uv run python scripts/steel_worktree.py up

steel-down: ## Stop and remove this worktree's own Steel, and its .env.steel
	$(BACKEND) uv run python scripts/steel_worktree.py down

steel-env: ## Point a shell at this worktree's Steel: eval "$$(make -s steel-env)"
	@sed 's/^/export /' .env.steel

# --- backend ----------------------------------------------------------------

install: ## Install backend and frontend dependencies
	$(BACKEND) uv sync --all-extras
	$(FRONTEND) npm ci

vault-key: ## Generate a vault key: export SRO_VAULT_KEY=$$(make -s vault-key)
	@$(BACKEND) uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

migrate-vault-keys: ## Copy QA's old-scheme vault passwords to the new S1 keys: dry-run by default, add apply=1 [delete-old=1]
	$(BACKEND) uv run python scripts/migrate_vault_keys.py $(if $(apply),--apply) $(if $(delete-old),--delete-old)

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

auth-secret: ## Generate a signing key for this deployment's own credentials
	@python3 -c "import secrets; print('SRO_AUTH_SECRET=' + secrets.token_urlsafe(48))"

token: ## Issue a credential: make token tenant=acme principal=you [days=30]
	@# `principal` has no default here, and the other targets that mint one keep
	@# theirs. Those drive a throwaway browser; this hands a token to a person.
	@# A credential names who is being observed, and every candidate is
	@# `(principal, signature)` -- so a forgotten argument does not fail, it
	@# quietly files that person's day under somebody else. It is how one
	@# operator became `devansh`, `operator` and `you` on two tenants, whose
	@# work can never be paired.
	@test -n "$(principal)" || { \
		echo "principal= is required: a credential names a person, and the wrong"; \
		echo "name splits their work from itself. Try:"; \
		echo "    make token tenant=$(or $(tenant),acme) principal=<who it is for>"; \
		exit 2; }
	@$(BACKEND) uv run python -m sro.cli.mint $(or $(tenant),acme) $(principal) --days $(or $(days),30)

observe: ## Read or change a tenant's observation policy: make observe tenant=acme args="--on"
	@$(BACKEND) uv run python -m sro.cli.observe $(or $(tenant),acme) $(args)

read-gestures: ## Read each named tenant's unread gestures, once: make read-gestures tenants="acme new"
	@$(BACKEND) uv run python -m sro.cli.read_cron $(or $(tenants),acme)

images: ## Build both deployment images, tagged with this commit: make images [api=http://host:8000]
	@# The web image bakes its API url and the extension's origin at build time
	@# -- Next inlines `NEXT_PUBLIC_*` and evaluates `headers()` during the
	@# build -- so an image is per environment until the console is proxied.
	@# See docs/18-deployment.md.
	@rev=$$(git rev-parse --short HEAD); \
	docker build --build-context page=new-chrome-extension/src/page \
		-t ai-sro-backend:$$rev --build-arg REVISION=$$rev backend/ && \
	docker build -t ai-sro-web:$$rev \
		--build-arg NEXT_PUBLIC_API_URL=$(or $(api),http://localhost:8000) \
		--build-arg NEXT_PUBLIC_EXTENSION_ORIGINS=$(or $(origins),chrome-extension://onfmljaebeipeiinflhgdochbcjeoehl) \
		frontend/ && \
	echo "built ai-sro-backend:$$rev and ai-sro-web:$$rev"

types: ## Regenerate frontend API types from the backend OpenAPI document
	$(BACKEND) uv run python -m sro.interface.http.export_openapi > ../frontend/openapi.json
	$(FRONTEND) npm run generate:types

gen-deployment: ## Tell the extension which deployment it is for: make gen-deployment api=http://host:8088/api console=http://host:8088
	@# The extension has no build step, so what is in the tree is what gets
	@# loaded: a QA build and a production build differ by the generated file
	@# this writes. An operator then pastes a credential and nothing else.
	@test -n "$(api)" || { echo "api= is required, e.g. api=http://10.11.9.25:8088/api"; exit 2; }
	$(BACKEND) uv run python scripts/write_deployment.py --api $(api) --console $(or $(console),)

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
	$(BACKEND) uv run mypy src tests evals
	$(BACKEND) uv run lint-imports

check-code-notes: ## docs/code-notes/ anchors still point at the line they name
	$(BACKEND) uv run python scripts/check_code_notes.py

eval: ## LIVE EVAL (spends model money): real local cases, report + gate: make eval suite=reader tenant=acme [baseline=1] [limit=N]
	$(BACKEND) uv run python -m evals run --suite $(suite) --tenant $(tenant) $(if $(baseline),--baseline,) $(if $(limit),--limit $(limit),)

eval-ci: ## The committed redacted cases, offline: prompts render, answers conform, scores hold [live=1]
	$(BACKEND) uv run python -m evals ci $(if $(live),--live,)

eval-redact: ## Redacted copies of the local cases, for a person to read before committing any
	$(BACKEND) uv run python -m evals redact --suite $(suite) --tenant $(tenant)

lint-frontend: ## eslint + tsc
	$(FRONTEND) npm run lint
	$(FRONTEND) npm run typecheck

lint-extension: ## no-undef over the extension, which has no build step to catch it
	cd new-chrome-extension && ../frontend/node_modules/.bin/eslint .

format: ## Autoformat both sides
	$(BACKEND) uv run ruff check --fix .
	$(BACKEND) uv run ruff format .
	$(FRONTEND) npm run format

test: test-unit test-replay test-integration ## Unit + replay + integration tests

test-unit: ## Fast tests. No Docker, no network.
	$(BACKEND) uv run pytest tests/unit -q

test-replay: ## Every recorded RunWorkflow history replays on the current workflow code
	$(BACKEND) uv run pytest tests/replay -q

record-histories: ## Record RunWorkflow histories from the real-Temporal tests (needs `make up`)
	$(BACKEND) SRO_RECORD_HISTORIES=1 uv run pytest tests/integration/test_run_workflow.py -q

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

# Beside the rig's rather than replacing it: the same measurement from the
# other store, so the two can be read against each other until phase 7 deletes
# the rig and its target with it.
offer-replay: ## Would the offer name the right job? The store's gestures through the real matcher, no browser
	$(BACKEND) uv run python scripts/dry_run.py --replay /tmp/offer-replay.json > /dev/null && node ../new-chrome-extension/scripts/offer-replay.mjs /tmp/offer-replay.json

measure: ## What this system has actually done, and what every number stands on
	@# Reads only. Every line carries a standing -- warehouse, mail, local,
	@# recorded, none -- because the argument about whether this direction is
	@# working is never about arithmetic, it is about what the number was
	@# measured on. `tenant=` narrows it; `questions=` also plans those lookups.
	$(BACKEND) uv run python scripts/measure.py $(if $(tenant),--tenant $(tenant),) \
		--questions scripts/measure-questions.txt $(if $(json),--json $(json),)

press-report: ## What one press of each mined job would write: make press-report [tenants="acme new"]
	@# Reads only, and the questions are the ones that found three defects in
	@# a day: which Saves write twice (the shape the replay refuses), which
	@# steps use which, and whether any job takes another job's output. Run it
	@# ON a deployment to measure that deployment.
	$(BACKEND) uv run python scripts/what_one_press_writes.py $(or $(tenants),)

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

smoke: ## Does a DEPLOYMENT work from outside itself: make smoke at=http://host:8088 [DOCKER="sudo docker"]
	@# Run after every deploy. Not a substitute for the suite -- it asks the
	@# one question a suite cannot: whether the urls this system hands to a
	@# browser name anything a browser can reach. Every defect on the first day
	@# of deploying was on one of those edges. See backend/scripts/smoke.py.
	@test -n "$(at)" || { echo "at= is required: make smoke at=http://<host>:<port>"; exit 2; }
	@# Hashed here, on the host, and handed in -- smoke.py runs inside the api
	@# container, where the "repository" it would otherwise read is the very
	@# file /health hashes, so a check computed in there could never fail.
	@page_code=$$(python3 -c "import hashlib; print(hashlib.sha256(open('new-chrome-extension/src/page/page-code.js','rb').read()).hexdigest())") && \
	$(DEPLOY) exec -T api python scripts/smoke.py $(at) $$page_code

check: lint test test-contract test-frontend test-extension test-browser ## What CI runs
