"""The registry of datasets the pipeline downloads. One entry per source."""

from dataclasses import dataclass
from typing import Literal

Kind = Literal["kaggle", "http", "fx", "wikidata"]

KAGGLE_API = "https://www.kaggle.com/api/v1/datasets/download"


@dataclass(frozen=True)
class Source:
    name: str
    description: str
    kind: Kind
    version: str
    ref: str = ""  # kaggle: "owner/slug"
    files: tuple[str, ...] = ()  # kaggle: single files to fetch; empty = whole dataset
    urls: tuple[tuple[str, str], ...] = ()  # http: (filename, url)
    optional: bool = False  # only downloaded when named with --source
    browser_ua: bool = False  # send a browser User-Agent (Netflix serves HTML otherwise)


REGISTRY: tuple[Source, ...] = (
    Source(
        name="tmdb",
        description="TMDB + IMDb daily snapshot (2026-10-01 = version 1018)",
        kind="kaggle",
        ref="alanvourch/tmdb-movies-daily-updates",
        files=("TMDB_all_movies.csv",),
        version="1018",
    ),
    Source(
        name="rt_clapper",
        description="Rotten Tomatoes movies (Clapper); reviews file skipped",
        kind="kaggle",
        ref="andrezaza/clapper-massive-rotten-tomatoes-movies-and-reviews",
        files=("rotten_tomatoes_movies.csv",),
        version="4",
    ),
    Source(
        name="numbers_budgets",
        description="The Numbers: budgets and revenues",
        kind="kaggle",
        ref="dahvid/movie-budgets-and-revenues",
        version="1",
    ),
    Source(
        name="numbers_metrics",
        description="The Numbers: ultimate metrics, features and metadata",
        kind="kaggle",
        ref="michaelmatta0/movies-ultimate-metrics-features-and-metadata",
        version="1",
    ),
    Source(
        name="rt_legacy",
        description="Rotten Tomatoes movies (older Leone dataset), fallback only",
        kind="kaggle",
        ref="stefanoleone992/rotten-tomatoes-movies-and-critic-reviews-dataset",
        files=("rotten_tomatoes_movies.csv",),
        version="1",
        optional=True,
    ),
    Source(
        name="netflix",
        description="Netflix Top 10 weekly, per country (live file)",
        kind="http",
        urls=(
            (
                "all-weeks-countries.tsv",
                "https://www.netflix.com/tudum/top10/data/all-weeks-countries.tsv",
            ),
        ),
        version="live",
        browser_ua=True,
    ),
    Source(
        name="cpi",
        description="FRED CPIAUCSL (US CPI, all urban consumers)",
        kind="http",
        urls=(("CPIAUCSL.csv", "https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL"),),
        version="live",
    ),
    Source(
        name="fx",
        description="World Bank PA.NUS.FCRF: local currency units per USD, yearly",
        kind="fx",
        urls=(
            (
                "PA.NUS.FCRF.json",
                "https://api.worldbank.org/v2/country/all/indicator/PA.NUS.FCRF",
            ),
        ),
        version="live",
    ),
    Source(
        name="world_atlas",
        description="world-atlas TopoJSON country shapes (50m and 110m)",
        kind="http",
        urls=(
            ("countries-50m.json", "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-50m.json"),
            (
                "countries-110m.json",
                "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json",
            ),
        ),
        version="world-atlas@2",
    ),
    Source(
        name="countries_iso",
        description=(
            "ISO 3166 codes with UN M49 regions "
            "(lukes/ISO-3166-Countries-with-Regional-Codes, CC BY-SA 4.0)"
        ),
        kind="http",
        urls=(
            (
                "all.csv",
                "https://raw.githubusercontent.com/lukes/ISO-3166-Countries-with-Regional-Codes/145f1ad3caff212ed25f42b0ee2c8b92a75af895/all/all.csv",
            ),
        ),
        version="145f1ad",
    ),
    Source(
        name="wikidata",
        description="Wikidata crosswalk: IMDb id to RT / Metacritic / LUMIERE / enwiki, money",
        kind="wikidata",
        version="live",
    ),
)


def get(name: str) -> Source:
    for src in REGISTRY:
        if src.name == name:
            return src
    raise KeyError(f"unknown source {name!r}; known: {', '.join(s.name for s in REGISTRY)}")
