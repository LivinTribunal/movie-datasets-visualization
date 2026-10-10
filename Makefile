.PHONY: setup data validate test lint dev preview

setup:
	cd pipeline && uv sync
	cd app && npm ci

data:
	uv run --project pipeline movies acquire
	uv run --project pipeline movies reference
	uv run --project pipeline movies clean
	uv run --project pipeline movies join
	uv run --project pipeline movies derive
	uv run --project pipeline movies export

validate:
	uv run --project pipeline movies validate

test:
	cd pipeline && uv run pytest tests -q
	cd app && npm test

lint:
	cd pipeline && uv run ruff check . && uv run ruff format --check .
	cd app && npm run lint && npm run typecheck

dev:
	cd app && npm run dev

preview:
	cd app && npm run build && npm run preview
