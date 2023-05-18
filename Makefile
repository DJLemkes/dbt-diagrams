# Target section and Global definitions
# -----------------------------------------------------------------------------
.PHONY: all clean test run_server down black ruff code_checks

.DEFAULT_GOAL := help

help:
	$(info Make: Please run one of the targets)

all: fmt check test

install:
	poetry install

test:
	poetry run pytest tests

poetry:
	pip3 install --upgrade pip
	pip3 install poetry==1.6.1
	poetry install

black-check:
	poetry run black --check . || echo "Please run black to format your code"

black:
	poetry run black .

ruff:
	poetry run ruff --fix .

ruff-check:
	poetry run ruff .

mypy:
	poetry run mypy

check: black-check ruff-check mypy
	$(info Make: checks done!)

fmt: black ruff

run-api-dev:
	cd dbt_diagrams && uvicorn rest_api:app --reload
