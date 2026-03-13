.PHONY: setup-local-python

setup-local-python:
	uv sync --group dev
	uv run --group dev pre-commit install
