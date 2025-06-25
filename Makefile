# Target section and Global definitions
# -----------------------------------------------------------------------------
.PHONY: all clean test run_server ruff code_checks

.DEFAULT_GOAL := help

help:
	$(info Make: Please run one of the targets)

install:
	poetry install --all-extras

test:
	poetry run pytest tests

ruff:
	poetry run ruff --fix .

fmt: ruff

run-api-dev:
	cd dbt_diagrams && uvicorn rest_api:app --reload
