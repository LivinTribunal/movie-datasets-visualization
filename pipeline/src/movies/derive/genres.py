"""Derive stage: genre memberships with 1/n weights and Netflix genre shares per country.

Pure functions from frames to frames; only `run()` reads data/interim and data/reference and
writes data/interim/film_genres.parquet and country_genre_netflix.parquet. Netflix shares carry
`coverage` (chart score that reached a genre) and `fuzzy_share` (chart score matched fuzzily),
because unmatched and fuzzy-matched data must be shown as such in the app.
"""

import polars as pl

from movies import paths

DROPPED_GENRES = ["TV Movie"]  # deliberately has no family colour


def film_genres(films: pl.DataFrame, families: pl.DataFrame) -> pl.DataFrame:
    """One row per (film, genre) with `genre_weight = 1 / n` kept genres, so a film sums to 1."""
    exploded = (
        films.select("imdb_id", "genres")
        .explode("genres")
        .rename({"genres": "genre"})
        .filter(pl.col("genre").is_not_null() & ~pl.col("genre").is_in(DROPPED_GENRES))
    )
    unknown = sorted(set(exploded["genre"]) - set(families["genre"]))
    if unknown:
        raise ValueError(f"genres missing from genre_families.csv: {unknown}")
    return (
        exploded.unique(["imdb_id", "genre"], maintain_order=True)
        .join(families.select("genre", "family"), on="genre", how="left")
        .with_columns(genre_weight=1 / pl.len().over("imdb_id"))
    )


def netflix_country_genre(
    netflix: pl.DataFrame, titles: pl.DataFrame, film_genres_df: pl.DataFrame
) -> pl.DataFrame:
    """Genre shares of Netflix chart score per country and year.

    `share` sums to 1 over the matched chart score of a country-year; `coverage` is the matched
    fraction of all chart score and `fuzzy_share` the fraction matched by title similarity.
    """
    chart = (
        netflix.select("country_iso2", year=pl.col("week").dt.year(), score="score", title="title")
        .join(titles.select("title", "imdb_id", "method"), on="title", how="left")
        .with_columns(
            matched=pl.col("imdb_id").is_in(film_genres_df["imdb_id"].implode()).fill_null(False)
        )
    )
    keys = ["country_iso2", "year"]
    totals = chart.group_by(keys).agg(
        total=pl.col("score").sum(),
        matched=pl.col("score").filter(pl.col("matched")).sum(),
        fuzzy=pl.col("score").filter(pl.col("method") == "fuzzy").sum(),
    )
    shares = (
        chart.filter("matched")
        .join(film_genres_df, on="imdb_id")
        .group_by([*keys, "genre", "family"])
        .agg(score=(pl.col("score") * pl.col("genre_weight")).sum().cast(pl.Float64))
        .with_columns(share=pl.col("score") / pl.col("score").sum().over(keys))
    )
    return (
        shares.join(totals, on=keys)
        .select(
            *keys,
            "genre",
            "family",
            "score",
            "share",
            coverage=pl.col("matched") / pl.col("total"),
            fuzzy_share=pl.col("fuzzy") / pl.col("total"),
        )
        .sort([*keys, "genre"])
    )


def run() -> None:
    films = pl.read_parquet(paths.INTERIM / "films.parquet")
    tmdb = pl.read_parquet(paths.INTERIM / "tmdb.parquet")
    netflix = pl.read_parquet(paths.INTERIM / "netflix.parquet")
    titles = pl.read_parquet(paths.INTERIM / "netflix_titles.parquet")
    families = pl.read_csv(paths.REFERENCE / "genre_families.csv")

    genres = film_genres(films, families)
    genres.write_parquet(paths.INTERIM / "film_genres.parquet")

    matched = titles.filter(pl.col("imdb_id").is_not_null())["imdb_id"].unique()
    netflix_films = tmdb.filter(pl.col("imdb_id").is_in(matched.implode()))
    out = netflix_country_genre(netflix, titles, film_genres(netflix_films, families))
    out.write_parquet(paths.INTERIM / "country_genre_netflix.parquet")

    coverage = out.unique(["country_iso2", "year"])["coverage"]
    print(f"film_genres: {genres.height} rows, {genres['imdb_id'].n_unique()} films")
    print(
        f"country_genre_netflix: {out.height} rows, {out['country_iso2'].n_unique()} countries, "
        f"years {out['year'].min()}-{out['year'].max()}"
    )
    print(f"coverage min {coverage.min():.3f}, median {coverage.median():.3f}")
