"""Derive stage: analysis-ready columns computed from the joined films table.

Each `movies.derive.<name>` module has pure functions over frames and a `run()` that reads
data/interim/ and data/scraped/ and writes data/interim/<name>.parquet.
"""

from importlib import import_module

SOURCES = ("money",)


def run(names: list[str]) -> None:
    """Derive the named outputs, or all of them, in SOURCES order."""
    unknown = set(names) - set(SOURCES)
    if unknown:
        raise KeyError(f"unknown source(s) {sorted(unknown)}; known: {', '.join(SOURCES)}")
    for name in SOURCES:
        if not names or name in names:
            print(f"[derive {name}]", flush=True)
            import_module(f"movies.derive.{name}").run()
