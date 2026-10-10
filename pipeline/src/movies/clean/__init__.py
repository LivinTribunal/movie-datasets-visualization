"""Clean stage: one tidy Parquet per source in data/interim/.

Each `movies.clean.<source>` module has pure functions from raw frames to a tidy frame and a
`run()` that reads data/raw/ and data/reference/ and writes data/interim/<source>.parquet.
"""

from importlib import import_module

SOURCES = ("tmdb", "rt_clapper", "numbers", "netflix", "cpi", "fx")


def run(names: list[str]) -> None:
    """Clean the named sources, or all of them, in SOURCES order."""
    unknown = set(names) - set(SOURCES)
    if unknown:
        raise KeyError(f"unknown source(s) {sorted(unknown)}; known: {', '.join(SOURCES)}")
    for name in SOURCES:
        if not names or name in names:
            print(f"[clean {name}]", flush=True)
            import_module(f"movies.clean.{name}").run()
