"""Derive stage: ratings on 0-100 and the critic-audience gap.

`ratings()` is a pure function; only `run()` reads data/interim/films.parquet and writes
data/interim/ratings.parquet.
"""

import polars as pl

from movies import paths

# Averages of a few votes are noise, so a TMDB average under this many votes is left null.
TMDB_MIN_VOTES = 50


def ratings(films: pl.DataFrame) -> pl.DataFrame:
    """One row per film: every score on 0-100 and `gap = audience - critics`."""
    return films.select(
        "imdb_id",
        imdb_100=pl.col("imdb_rating").cast(pl.Float64) * 10,
        tmdb_100=pl.when(pl.col("vote_count") >= TMDB_MIN_VOTES).then(
            pl.col("vote_average").cast(pl.Float64) * 10
        ),
        tomatometer_100=pl.col("tomatometer").cast(pl.Float64),
        audience_100=pl.col("audience_score").cast(pl.Float64),
    ).with_columns(gap=pl.col("audience_100") - pl.col("tomatometer_100"))


def run() -> None:
    films = pl.read_parquet(paths.INTERIM / "films.parquet")
    out = ratings(films)
    out.write_parquet(paths.INTERIM / "ratings.parquet")

    print(f"ratings: {out.height} rows")
    for col in out.columns[1:]:
        print(f"  {col}: {out[col].is_not_null().sum()} non-null")
    print(f"gap mean {out['gap'].mean():.2f}, median {out['gap'].median():.2f}")
