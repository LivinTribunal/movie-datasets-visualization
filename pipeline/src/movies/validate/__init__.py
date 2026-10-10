"""Validate stage: schema and invariant checks on the committed app data."""

from importlib import import_module

SOURCES = ("app",)


def run() -> None:
    for name in SOURCES:
        print(f"[validate {name}]", flush=True)
        import_module(f"movies.validate.{name}").run()
