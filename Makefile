.DEFAULT_GOAL := help
SHELL := /bin/bash

API := api
WEB := web
PY  := $(API)/.venv/bin

.PHONY: help install dev-api dev-web build index test lint check docker run clean

help: ## Show this help
	@grep -hE '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Create the venv and install both sides
	python3 -m venv $(API)/.venv
	$(PY)/pip install -q -e "$(API)[dev]"
	cd $(WEB) && npm install

dev-api: ## Run the API with hot reload (localhost:8099)
	cd $(API) && .venv/bin/uvicorn nexus_card.main:app --reload --port 8099

dev-web: ## Run Vite with an /api proxy to the local API (localhost:5173)
	cd $(WEB) && npm run dev

build: ## Build the SPA into web/dist (served by the API)
	cd $(WEB) && npm run build

index: ## Rebuild the dense KB index (needs AWS Bedrock credentials)
	cd $(API) && .venv/bin/python scripts/build_index.py

test: ## Run the API test suite
	cd $(API) && .venv/bin/pytest -q

lint: ## Ruff + mypy + tsc
	cd $(API) && .venv/bin/ruff check src tests && .venv/bin/mypy
	cd $(WEB) && npx tsc -b --noEmit

check: lint test build ## Everything CI should run

docker: ## Build the production image
	docker build -f docker/Dockerfile -t nexus-card:latest .

run: build ## Build the SPA then serve everything from the API
	cd $(API) && .venv/bin/uvicorn nexus_card.main:app --port 8099

clean:
	rm -rf $(WEB)/dist $(WEB)/node_modules $(API)/.venv
