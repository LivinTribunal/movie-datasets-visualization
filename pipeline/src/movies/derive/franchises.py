"""Derive stage: franchise installments and rating/revenue changes, for task T6.

`franchises()` is a pure function; only `run()` reads data/scraped/tmdb_collection_parts.parquet and
data/interim/ and writes data/interim/franchises.parquet.
"""

import datetime as dt

import polars as pl

from movies import paths

SNAPSHOT = dt.date(2026, 10, 1)
MIN_RELEASED = 3


def _ratio(col: str, ref: pl.Expr) -> pl.Expr:
    return pl.when(ref != 0).then(pl.col(col) / ref)


def franchises(
    parts: pl.DataFrame, films: pl.DataFrame, ratings: pl.DataFrame, money: pl.DataFrame
) -> pl.DataFrame:
    """One row per released part of a collection with >= 3 released parts.

    Parts outside `films` keep their installment number but have null ratings and money.
    """
    by_coll = ["collection_id"]
    df = (
        parts.filter(pl.col("release_date").is_not_null() & (pl.col("release_date") <= SNAPSHOT))
        .with_columns(n_released=pl.len().over(by_coll))
        .filter(pl.col("n_released") >= MIN_RELEASED)
        .sort("collection_id", "release_date", "tmdb_id")
        .with_columns(installment=pl.int_range(pl.len()).over(by_coll) + 1)
        .join(films.select("tmdb_id", "imdb_id"), on="tmdb_id", how="left")
        .join(
            ratings.select("imdb_id", "imdb_100", "tomatometer_100", "audience_100"),
            on="imdb_id",
            how="left",
        )
        .join(money.select("imdb_id", "revenue_usd2025"), on="imdb_id", how="left")
        .sort("collection_id", "installment")
    )
    prev = pl.col("imdb_100").shift(1).over(by_coll)
    first = pl.col("imdb_100").first().over(by_coll)
    rev_prev = pl.col("revenue_usd2025").shift(1).over(by_coll)
    rev_first = pl.col("revenue_usd2025").first().over(by_coll)
    return df.with_columns(
        imdb_100_vs_prev=pl.col("imdb_100") - prev,
        imdb_100_vs_first=pl.col("imdb_100") - first,
        revenue_vs_prev=_ratio("revenue_usd2025", rev_prev),
        revenue_vs_first=_ratio("revenue_usd2025", rev_first),
    ).select(
        "collection_id", "collection_name", "installment", "n_released", "tmdb_id", "imdb_id",
        "title", "release_date", "imdb_100", "imdb_100_vs_prev", "imdb_100_vs_first",
        "tomatometer_100", "audience_100", "revenue_usd2025", "revenue_vs_prev",
        "revenue_vs_first",
    )  # fmt: skip


def run() -> None:
    parts = pl.read_parquet(paths.SCRAPED / "tmdb_collection_parts.parquet")
    films = pl.read_parquet(paths.INTERIM / "films.parquet", columns=["imdb_id", "tmdb_id"])
    ratings = pl.read_parquet(paths.INTERIM / "ratings.parquet")
    money = pl.read_parquet(paths.INTERIM / "money.parquet")
    out = franchises(parts, films, ratings, money)
    out.write_parquet(paths.INTERIM / "franchises.parquet")

    print(f"franchises: {out['collection_id'].n_unique()} collections, {out.height} films")
    print(f"  films with imdb_100: {out['imdb_100'].is_not_null().sum()}")
    second = out.filter(pl.col("installment") == 2)["imdb_100_vs_first"].median()
    print(f"  median imdb_100_vs_first at installment 2: {second}")
