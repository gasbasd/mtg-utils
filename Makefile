.PHONY: test lint coverage ci all

test:
	poetry run pytest -v -p no:cov

lint:
	poetry run ruff check mtg_utils tests

coverage:
	poetry run pytest --cov-report=term-missing --cov-report=html

ci: lint coverage

all: lint coverage
