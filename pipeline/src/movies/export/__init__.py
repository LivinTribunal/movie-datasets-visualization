"""Export stage: interim tables -> the app's data files in app/public/data/."""

from importlib import import_module

SOURCES = ("app",)


def run() -> None:
    for name in SOURCES:
        print(f"[export {name}]", flush=True)
        import_module(f"movies.export.{name}").run()
