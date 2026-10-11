"""Export stage: the app's data files, written to app/public/data/.

Pure functions build the frames and `to_columns` turns one into columnar JSON
(`{"columns": {name: [...]}}`); only `run()` reads data/interim and writes files. Output is
deterministic (sorted, no timestamps) so a re-run gives no diff.
"""

import json
import shutil
from pathlib import Path

import polars as pl

from movies import paths
from movies.validate.app import SCHEMA

NOTES = [
    "Money is converted at release-year World Bank rates and inflated with CPI to 2025 USD.",
    "Films before 1947 have no 2025 USD value: the CPI series starts in 1947.",
    "Budgets under $1,000 and revenues under $10,000 are dropped as unreliable.",
    "Fuzzy title matches to The Numbers are flagged (money_fuzzy).",
    "Genre shares use 1/n weights: a film with n genres counts 1/n in each.",
    "The TMDB average is null under 50 votes.",
    "Netflix shares cover only matched titles; see the coverage column.",
    "Cinema genre shares come from LUMIERE admissions of notable films only; UK and Ireland "
    "admissions are LUMIERE estimates, and the combined UK+Ireland market counts as the UK.",
]


def _converted(name: str, currency: str) -> pl.Expr:
    return (
        (pl.col(currency).is_not_null() & (pl.col(currency) != "USD")).fill_null(False).alias(name)
    )


def films_table(
    films: pl.DataFrame, money: pl.DataFrame, ratings: pl.DataFrame, film_genres: pl.DataFrame
) -> pl.DataFrame:
    """One row per notable film or film with both RT scores, with money and rating columns."""
    genres = film_genres.group_by("imdb_id").agg(
        genres=pl.col("genre"), families=pl.col("family").unique(maintain_order=True)
    )
    df = (
        films.join(money, on="imdb_id", how="left")
        .join(ratings, on="imdb_id", how="left")
        .join(genres, on="imdb_id", how="left")
        .filter(
            pl.col("notable")
            | (pl.col("tomatometer_100").is_not_null() & pl.col("audience_100").is_not_null())
        )
        .with_columns(
            pl.col("genres").fill_null([]),
            pl.col("families").fill_null([]),
            _converted("budget_converted", "budget_currency"),
            _converted("revenue_converted", "revenue_currency"),
            money_fuzzy=(
                (pl.col("numbers_match") == "fuzzy")
                & ((pl.col("budget_src") == "numbers") | (pl.col("revenue_src") == "numbers"))
            ).fill_null(False),
            countries=pl.col("production_countries").fill_null([]),
            budget_usd2025=pl.col("budget_usd2025").round(0).cast(pl.Int64),
            revenue_usd2025=pl.col("revenue_usd2025").round(0).cast(pl.Int64),
            roi=pl.col("roi").round(3),
            imdb_100=pl.col("imdb_100").round(1),
            tmdb_100=pl.col("tmdb_100").round(1),
            tomatometer_100=pl.col("tomatometer_100").round(1),
            audience_100=pl.col("audience_100").round(1),
            metascore_100=pl.col("metascore_100").round(1),
            mc_user_100=pl.col("mc_user_100").round(1),
            letterboxd_100=pl.col("letterboxd_100").round(1),
            gap=pl.col("gap").round(1),
        )
    )
    return df.select(SCHEMA["films.json"]).sort("imdb_id")


def genre_year(films: pl.DataFrame, money: pl.DataFrame, film_genres: pl.DataFrame) -> pl.DataFrame:
    """Genre weight, votes and revenue per (subset, year, genre); notable films are in both."""
    base = (
        films.select("imdb_id", "year", "imdb_votes", "notable")
        .filter(pl.col("year").is_not_null())
        .join(money.select("imdb_id", "revenue_usd2025"), on="imdb_id", how="left")
        .join(film_genres, on="imdb_id")
    )
    both = pl.concat(
        [
            base.with_columns(subset=pl.lit("working")),
            base.filter("notable").with_columns(subset=pl.lit("notable")),
        ]
    )
    return (
        both.group_by("subset", "year", "genre", "family")
        .agg(
            films=pl.col("genre_weight").sum().round(4),
            votes=(pl.col("genre_weight") * pl.col("imdb_votes")).sum().round(1),
            revenue=(pl.col("genre_weight") * pl.col("revenue_usd2025")).sum(),
            revenue_films=pl.col("revenue_usd2025").is_not_null().sum().cast(pl.Int64),
        )
        .with_columns(
            revenue_usd2025=pl.when(pl.col("revenue_films") > 0)
            .then(pl.col("revenue").round(0).cast(pl.Int64))
            .otherwise(None)
        )
        .select(SCHEMA["genre_year.json"])
        .sort("subset", "year", "genre")
    )


def franchises_table(df: pl.DataFrame) -> pl.DataFrame:
    return (
        df.with_columns(
            year=pl.col("release_date").dt.year().cast(pl.Int64),
            imdb_100=pl.col("imdb_100").round(1),
            imdb_100_vs_prev=pl.col("imdb_100_vs_prev").round(1),
            imdb_100_vs_first=pl.col("imdb_100_vs_first").round(1),
            tomatometer_100=pl.col("tomatometer_100").round(1),
            audience_100=pl.col("audience_100").round(1),
            revenue_usd2025=pl.col("revenue_usd2025").round(0).cast(pl.Int64),
            revenue_vs_prev=pl.col("revenue_vs_prev").round(3),
            revenue_vs_first=pl.col("revenue_vs_first").round(3),
        )
        .select(SCHEMA["franchises.json"])
        .sort("collection_id", "installment")
    )


def to_columns(df: pl.DataFrame) -> dict[str, list]:
    return {c: df[c].to_list() for c in df.columns}


def _write(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, separators=(",", ":"), ensure_ascii=False))
    print(f"{path.name}: {path.stat().st_size / 1e6:.2f} MB")


def _write_table(name: str, df: pl.DataFrame) -> None:
    _write(paths.APP_DATA / name, {"columns": to_columns(df)})


def run() -> None:
    interim = paths.INTERIM
    films = pl.read_parquet(interim / "films.parquet")
    money = pl.read_parquet(interim / "money.parquet")
    ratings = pl.read_parquet(interim / "ratings.parquet")
    fg = pl.read_parquet(interim / "film_genres.parquet")
    netflix = pl.read_parquet(interim / "country_genre_netflix.parquet")
    paths.APP_DATA.mkdir(parents=True, exist_ok=True)

    films_out = films_table(films, money, ratings, fg)
    _write_table("films.json", films_out)
    _write_table("genre_year.json", genre_year(films, money, fg))
    lumiere_path = interim / "country_genre_lumiere.parquet"
    sources = [("netflix", netflix)]
    if lumiere_path.exists():
        sources.append(("lumiere", pl.read_parquet(lumiere_path)))
    else:
        print("lumiere cinema shares skipped: run `movies scrape --source lumiere` and derive")
    country_genre = pl.concat(
        [
            df.with_columns(
                source=pl.lit(name),
                share=pl.col("share").round(4),
                coverage=pl.col("coverage").round(4),
                fuzzy_share=pl.col("fuzzy_share").round(4),
                estimated_share=pl.col("estimated_share").round(4),
            ).select(SCHEMA["country_genre.json"])
            for name, df in sources
        ]
    )
    _write_table("country_genre.json", country_genre)
    countries = pl.read_csv(
        paths.REFERENCE / "countries.csv", schema_overrides={"iso_numeric": pl.String}
    )
    _write_table("countries.json", countries.select(SCHEMA["countries.json"]))
    families = pl.read_csv(paths.REFERENCE / "genre_families.csv")
    _write_table("genre_families.json", families.select(SCHEMA["genre_families.json"]))
    franchises_path = interim / "franchises.parquet"
    franchises_out = None
    if franchises_path.exists():
        franchises_out = franchises_table(pl.read_parquet(franchises_path))
        _write_table("franchises.json", franchises_out)
    else:
        print("franchises.json skipped: run `movies scrape --source tmdb_collections` and derive")
    shutil.copyfile(
        paths.RAW / "world_atlas" / "countries-110m.json", paths.APP_DATA / "countries.topo.json"
    )
    _write(
        paths.APP_DATA / "meta.json",
        {
            "snapshots": {"tmdb_imdb": "2026-10-01", "netflix": "2026-09-27"},
            "base_year": 2025,
            "counts": {
                "films": films_out.height,
                "notable": int(films_out["notable"].sum()),
                "with_budget": films_out["budget_usd2025"].count(),
                "with_revenue": films_out["revenue_usd2025"].count(),
                "with_gap": films_out["gap"].count(),
                "netflix_countries": netflix["country_iso2"].n_unique(),
                **(
                    {
                        "lumiere_markets": country_genre.filter(pl.col("source") == "lumiere")[
                            "country_iso2"
                        ].n_unique()
                    }
                    if len(sources) > 1
                    else {}
                ),
                **(
                    {"franchises": franchises_out["collection_id"].n_unique()}
                    if franchises_out is not None
                    else {}
                ),
            },
            "notes": NOTES,
        },
    )
