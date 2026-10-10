.PHONY: setup data validate test lint dev preview

setup:
	cd pipeline && uv sync
	@echo "app not set up yet (npm ci skipped)"

# full local rebuild; only the acquire stage exists so far
data:
	uv run --project pipeline movies acquire

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
