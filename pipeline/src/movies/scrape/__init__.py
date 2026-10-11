"""Scrape stage: parsed results of web and API scrapes, written to data/scraped."""

from importlib import import_module

SOURCES = ("tmdb_collections", "metacritic", "letterboxd", "lumiere")


def run(name: str) -> None:
    """Scrape one source: fetch into data/cache, parse the cache, write data/scraped."""
    if name not in SOURCES:
        raise KeyError(f"unknown source {name!r}; known: {', '.join(SOURCES)}")
    import_module(f"movies.scrape.{name}").build()
