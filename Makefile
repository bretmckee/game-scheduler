.PHONY: setup-local-python act-ci run-local-staging

setup-local-python:
	uv sync --group dev
	uv run --group dev pre-commit install

act-ci:
	scripts/run-act.sh push --job code-quality

run-local-staging: ## Run published images locally using dev credentials (avoids touching shared staging)
	IMAGE_REGISTRY=ghcr.io/game-scheduler/ IMAGE_TAG=$(IMAGE_TAG) \
		docker compose -f compose.yaml -f compose.staging.yaml --env-file config/env.dev up -d
