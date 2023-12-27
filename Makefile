# Target section and Global definitions
# -----------------------------------------------------------------------------
.PHONY: all clean test run_server ruff code_checks

.DEFAULT_GOAL := help

help:
	$(info Make: Please run one of the targets)

all: fmt check test

install:
	poetry install --all-extras

test:
	poetry run pytest tests

poetry:
	pip3 install poetry==1.6.1
	pip3 install "poetry-dynamic-versioning[plugin]"==1.2.0

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
