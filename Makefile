# Convenience targets. Run `make help` for the list.
.DEFAULT_GOAL := help
MODEL ?= qwen2.5:7b-instruct

.PHONY: help setup up down model logs test anonymize review shell

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

setup: ## Create .env from the template (edit it afterwards)
	@test -f .env || cp .env.example .env
	@echo "Created .env (copy of .env.example). Edit it, then run: make up"

up: ## Build and start the stack (pipeline + ollama)
	docker compose up -d --build

down: ## Stop the stack
	docker compose down

model: ## Pull the local LLM into the ollama service (MODEL=...)
	docker compose exec ollama ollama pull $(MODEL)

logs: ## Tail logs
	docker compose logs -f

test: ## Run the test suite inside the pipeline container
	docker compose exec pipeline python -m pytest -q

shell: ## Open a shell in the pipeline container
	docker compose exec pipeline bash

# Example: make anonymize CASE=CASE-2026-001 FILE=/data/zaak.docx
anonymize: ## Anonymize a document (CASE=... FILE=...)
	docker compose exec pipeline python cli.py anonymize --case $(CASE) $(FILE)

review: ## Show a case's detections (CASE=...)
	docker compose exec pipeline python cli.py review --case $(CASE)
