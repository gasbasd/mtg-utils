.PHONY: test lint typecheck coverage ci all install-hooks

test:
	poetry run pytest -v -p no:cov

lint:
	poetry run ruff check mtg_utils tests

typecheck:
	poetry run pyright

coverage:
	poetry run pytest --cov=mtg_utils --cov-report=term-missing --cov-report=html

ci: lint typecheck coverage

all: lint typecheck coverage

install-hooks:
	cp .githooks/pre-commit .git/hooks/pre-commit
	chmod +x .git/hooks/pre-commit
