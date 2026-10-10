.PHONY: setup data validate test lint dev preview

setup:
	cd pipeline && uv sync
	@echo "app not set up yet (npm ci skipped)"

# full local rebuild; join, derive and export do not exist yet
data:
	uv run --project pipeline movies acquire
	uv run --project pipeline movies reference
	uv run --project pipeline movies clean

validate:
	@echo "validate stage not written yet"

test:
	cd pipeline && uv run pytest tests -q
	@echo "app not set up yet (vitest skipped)"

lint:
	cd pipeline && uv run ruff check . && uv run ruff format --check .
	@echo "app not set up yet (eslint and tsc skipped)"

dev:
	@echo "app not set up yet"

preview:
	@echo "app not set up yet"
