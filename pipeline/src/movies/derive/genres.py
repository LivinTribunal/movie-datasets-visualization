"""Derive stage: genre memberships with 1/n weights, Netflix and LUMIERE genre shares.

Pure functions from frames to frames; only `run()` reads data/interim and data/reference and
writes data/interim/film_genres.parquet, country_genre_netflix.parquet and
country_genre_lumiere.parquet (cinema admissions per market, when the scrape exists).
Netflix shares carry `coverage` (chart score that reached a genre) and `fuzzy_share` (chart
score matched fuzzily), because unmatched and fuzzy-matched data must be shown as such in the app.
"""

import polars as pl

from movies import paths

DROPPED_GENRES = ["TV Movie"]  # deliberately has no family colour
# A market-year with fewer distinct films gives noisy shares, so it is dropped.
LUMIERE_MIN_FILMS = 20


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
        fuzzy=pl.col("score").filter(pl.col("matched") & (pl.col("method") == "fuzzy")).sum(),
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
            estimated_share=pl.lit(0.0),  # chart scores are never estimated
        )
        .sort([*keys, "genre"])
    )


def lumiere_country_genre(
    lumiere: pl.DataFrame, film_genres_df: pl.DataFrame, iso2: set[str] | list[str]
) -> pl.DataFrame:
    """Genre shares of cinema admissions per market (`country_iso2`) and year.

    Same columns as `netflix_country_genre`: `share` sums to 1 over the admissions of films with
    genres, `coverage` is that fraction of all admissions, `estimated_share` the fraction LUMIERE
    estimated. LUMIERE matches by Wikidata id, so `fuzzy_share` is 0. The combined `GB_IE`
    market counts as GB, and only for film-years without a GB row of their own.
    """
    unknown = sorted(set(lumiere["market"]) - set(iso2) - {"GB_IE"})
    if unknown:
        raise ValueError(f"LUMIERE markets missing from countries.csv: {unknown}")
    gb_years = lumiere.filter(pl.col("market") == "GB").select("imdb_id", "year").unique()
    rows = (
        lumiere.join(gb_years, on=["imdb_id", "year"], how="anti")
        .filter(pl.col("market") == "GB_IE")
        .with_columns(market=pl.lit("GB"))
        .vstack(lumiere.filter(pl.col("market") != "GB_IE"))
        .rename({"market": "country_iso2"})
    )
    keys = ["country_iso2", "year"]
    rows = rows.with_columns(has_genre=pl.col("imdb_id").is_in(film_genres_df["imdb_id"].implode()))
    totals = (
        rows.group_by(keys)
        .agg(
            total=pl.col("admissions").sum(),
            matched=pl.col("admissions").filter(pl.col("has_genre")).sum(),
            estimated=pl.col("admissions").filter(pl.col("estimated")).sum(),
            films=pl.col("imdb_id").n_unique(),
        )
        .filter(pl.col("films") >= LUMIERE_MIN_FILMS)
    )
    shares = (
        rows.filter("has_genre")
        .join(film_genres_df, on="imdb_id")
        .group_by([*keys, "genre", "family"])
        .agg(score=(pl.col("admissions") * pl.col("genre_weight")).sum().cast(pl.Float64))
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
            fuzzy_share=pl.lit(0.0),
            estimated_share=pl.col("estimated") / pl.col("total"),
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

    lumiere_path = paths.SCRAPED / "lumiere.parquet"
    if lumiere_path.exists():
        countries = pl.read_csv(
            paths.REFERENCE / "countries.csv", schema_overrides={"iso_numeric": pl.String}
        )
        cinema = lumiere_country_genre(pl.read_parquet(lumiere_path), genres, countries["iso2"])
        cinema.write_parquet(paths.INTERIM / "country_genre_lumiere.parquet")
        print(
            f"country_genre_lumiere: {cinema.height} rows, "
            f"{cinema['country_iso2'].n_unique()} markets, "
            f"years {cinema['year'].min()}-{cinema['year'].max()}"
        )
    else:
        print("lumiere.parquet not found; no cinema genre shares")

    coverage = out.unique(["country_iso2", "year"])["coverage"]
    print(f"film_genres: {genres.height} rows, {genres['imdb_id'].n_unique()} films")
    print(
        f"country_genre_netflix: {out.height} rows, {out['country_iso2'].n_unique()} countries, "
        f"years {out['year'].min()}-{out['year'].max()}"
    )
    print(f"coverage min {coverage.min():.3f}, median {coverage.median():.3f}")
