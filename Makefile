# Target section and Global definitions
# -----------------------------------------------------------------------------
.PHONY: all clean test run_server ruff code_checks

.DEFAULT_GOAL := help

help:
	$(info Make: Please run one of the targets)

all: fmt check test

install:
	poetry install --all-extras
	poetry self add "poetry-dynamic-versioning[plugin]"

test:
	poetry run pytest tests

ruff:
	poetry run ruff --fix .

ruff-check:
	poetry run ruff .

mypy:
	poetry run mypy

check: ruff-check mypy
	$(info Make: checks done!)

fmt: ruff

run-api-dev:
	cd dbt_diagrams && uvicorn rest_api:app --reload
