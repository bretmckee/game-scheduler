.PHONY: setup-local-python act-ci run-local-staging restamp-mutmut-baseline

setup-local-python:
	uv sync --group dev
	uv run --group dev pre-commit install

act-ci:
	scripts/run-act.sh push --job code-quality

run-local-staging: ## Run published images locally using dev credentials (avoids touching shared staging)
	IMAGE_REGISTRY=ghcr.io/game-scheduler/ IMAGE_TAG=$(IMAGE_TAG) \
		docker compose -f compose.yaml -f compose.staging.yaml --env-file config/env.dev up -d

restamp-mutmut-baseline: ## Full cold mutation pass over source_paths, then rebuild mutmut-baseline.json from the complete store (~5-10 min); ledger refuses if any verdict is missing
	rm -rf mutants
	TESTING=true uv run --group dev python scripts/run-mutmut.py run
	uv run --group dev python scripts/mutmut_ledger.py snapshot
