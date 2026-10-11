"""Derive stage: ratings on 0-100 and the critic-audience gap.

`ratings()` is a pure function; only `run()` reads data/interim/films.parquet and writes
data/interim/ratings.parquet.
"""

import polars as pl

from movies import paths

# Averages of a few votes are noise, so a TMDB average under this many votes is left null.
TMDB_MIN_VOTES = 50
# A handful of Metacritic user ratings is noise, often review-bombing, so the score is left null.
MC_MIN_USER_RATINGS = 10


def ratings(
    films: pl.DataFrame,
    metacritic: pl.DataFrame | None = None,
    letterboxd: pl.DataFrame | None = None,
) -> pl.DataFrame:
    """One row per film: every score on 0-100 and `gap = audience - critics`.

    The scraped Metacritic and Letterboxd frames are optional; without them their columns are null.
    Letterboxd shows an average only once a film has enough ratings, so it gets no extra threshold.
    """
    out = films.select(
        "imdb_id",
        imdb_100=pl.col("imdb_rating").cast(pl.Float64) * 10,
        tmdb_100=pl.when(pl.col("vote_count") >= TMDB_MIN_VOTES).then(
            pl.col("vote_average").cast(pl.Float64) * 10
        ),
        tomatometer_100=pl.col("tomatometer").cast(pl.Float64),
        audience_100=pl.col("audience_score").cast(pl.Float64),
    )
    if metacritic is None:
        out = out.with_columns(
            metascore_100=pl.lit(None, pl.Float64), mc_user_100=pl.lit(None, pl.Float64)
        )
    else:
        mc = metacritic.select(
            "imdb_id",
            metascore_100=pl.col("metascore").cast(pl.Float64),
            mc_user_100=pl.when(pl.col("mc_user_ratings") >= MC_MIN_USER_RATINGS).then(
                pl.col("mc_user_score").cast(pl.Float64) * 10
            ),
        )
        out = out.join(mc, on="imdb_id", how="left")
    if letterboxd is None:
        out = out.with_columns(letterboxd_100=pl.lit(None, pl.Float64))
    else:
        lb = letterboxd.select(
            "imdb_id", letterboxd_100=pl.col("letterboxd_avg").cast(pl.Float64) * 20
        )
        out = out.join(lb, on="imdb_id", how="left")
    return out.select(
        "imdb_id",
        "imdb_100",
        "tmdb_100",
        "tomatometer_100",
        "metascore_100",
        "audience_100",
        "mc_user_100",
        "letterboxd_100",
        gap=pl.col("audience_100") - pl.col("tomatometer_100"),
    )


def _read_scraped(name: str, nulls: str) -> pl.DataFrame | None:
    path = paths.SCRAPED / name
    if path.exists():
        return pl.read_parquet(path)
    print(f"{name} not found; {nulls} stay null")
    return None


def run() -> None:
    films = pl.read_parquet(paths.INTERIM / "films.parquet")
    out = ratings(
        films,
        _read_scraped("metacritic.parquet", "metascore_100 and mc_user_100"),
        _read_scraped("letterboxd.parquet", "letterboxd_100"),
    )
    out.write_parquet(paths.INTERIM / "ratings.parquet")

    print(f"ratings: {out.height} rows")
    for col in out.columns[1:]:
        print(f"  {col}: {out[col].is_not_null().sum()} non-null")
    print(f"gap mean {out['gap'].mean():.2f}, median {out['gap'].median():.2f}")
