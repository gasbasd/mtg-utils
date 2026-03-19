.PHONY: test lint coverage all

test:
	poetry run pytest -v

lint:
	poetry run ruff check mtg_utils tests

coverage:
	poetry run pytest --cov=mtg_utils --cov-report=term-missing --cov-report=html --cov-fail-under=100

all: lint coverage
