"""Derive stage: genre memberships with 1/n weights, Netflix and LUMIERE genre shares.

Pure functions from frames to frames; only `run()` reads data/interim and data/reference and
writes data/interim/film_genres.parquet, country_genre_netflix.parquet,
country_genre_lumiere.parquet (cinema admissions per market, when the scrape exists),
country_genre_production.parquet (films produced per country) and country_genre_us.parquet
(US cinema gross), and imdb_genre_year.parquet (IMDb genre shares per year, when imdb.parquet
exists). Every country table ends with `entries`, the distinct films behind a row's
country-year.
Netflix shares carry `coverage` (chart score that reached a genre) and `fuzzy_share` (chart
score matched fuzzily), because unmatched and fuzzy-matched data must be shown as such in the app.
"""

import polars as pl

from movies import paths

DROPPED_GENRES = ["TV Movie"]  # deliberately has no family colour
# A market-year with fewer distinct films gives noisy shares, so it is dropped.
LUMIERE_MIN_FILMS = 20
SHORTS_UNTIL = 1920  # before 1920 most films were shorts, so they count; later only features


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
        entries=pl.col("imdb_id").filter(pl.col("matched")).n_unique(),
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
            entries="entries",
        )
        .sort([*keys, "genre"])
    )


def kobis_as_lumiere(kobis: pl.DataFrame) -> pl.DataFrame:
    """KOBIS rows in the LUMIERE long shape: market KR, no lumiere_id, never estimated."""
    return kobis.select(
        "imdb_id",
        lumiere_id=pl.lit(None, dtype=pl.String),
        market=pl.lit("KR"),
        year=pl.col("year").cast(pl.Int16),
        admissions=pl.col("admissions").cast(pl.Int64),
        estimated=pl.lit(False),
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
            entries=pl.col("imdb_id").filter(pl.col("has_genre")).n_unique(),
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
            entries="entries",
        )
        .sort([*keys, "genre"])
    )


def production_country_genre(films: pl.DataFrame, film_genres_df: pl.DataFrame) -> pl.DataFrame:
    """Genre shares of films produced per country and release year.

    `score` is the summed genre weight, so a co-production counts fully in each of its countries.
    Films without a year or a country are dropped. Nothing is estimated or fuzzy-matched, so
    `coverage` is 1 and `fuzzy_share` and `estimated_share` are 0.
    """
    keys = ["country_iso2", "year"]
    rows = (
        films.select("imdb_id", "year", country_iso2="production_countries")
        .explode("country_iso2")
        .drop_nulls(["year", "country_iso2"])
        .unique(["imdb_id", *keys])
        .join(film_genres_df, on="imdb_id")
    )
    entries = rows.group_by(keys).agg(entries=pl.col("imdb_id").n_unique())
    shares = (
        rows.group_by([*keys, "genre", "family"])
        .agg(score=pl.col("genre_weight").sum().cast(pl.Float64))
        .with_columns(share=pl.col("score") / pl.col("score").sum().over(keys))
    )
    return (
        shares.join(entries, on=keys)
        .select(
            pl.col("country_iso2"),
            pl.col("year").cast(pl.Int16),
            "genre",
            "family",
            "score",
            "share",
            coverage=pl.lit(1.0),
            fuzzy_share=pl.lit(0.0),
            estimated_share=pl.lit(0.0),
            entries="entries",
        )
        .sort([*keys, "genre"])
    )


def us_cinema_country_genre(
    films: pl.DataFrame, film_genres_df: pl.DataFrame, min_films: int = LUMIERE_MIN_FILMS
) -> pl.DataFrame:
    """Genre shares of US domestic gross per release year, as one country (`US`).

    `score` is gross times genre weight. `coverage` is the gross of films with genres over all
    gross of the year, `fuzzy_share` the part of it matched to The Numbers by title similarity.
    Years with fewer than `min_films` films are dropped.
    """
    keys = ["country_iso2", "year"]
    rows = (
        films.filter(pl.col("year").is_not_null() & (pl.col("numbers_domestic_gross") > 0))
        .select(
            "imdb_id",
            "year",
            gross="numbers_domestic_gross",
            fuzzy=pl.col("numbers_match") == "fuzzy",
        )
        .with_columns(
            country_iso2=pl.lit("US"),
            has_genre=pl.col("imdb_id").is_in(film_genres_df["imdb_id"].implode()),
        )
    )
    totals = (
        rows.group_by(keys)
        .agg(
            total=pl.col("gross").sum(),
            matched=pl.col("gross").filter(pl.col("has_genre")).sum(),
            fuzzy=pl.col("gross").filter(pl.col("has_genre") & pl.col("fuzzy")).sum(),
            films=pl.col("imdb_id").n_unique(),
            entries=pl.col("imdb_id").filter(pl.col("has_genre")).n_unique(),
        )
        .filter(pl.col("films") >= min_films)
    )
    shares = (
        rows.filter("has_genre")
        .join(film_genres_df, on="imdb_id")
        .group_by([*keys, "genre", "family"])
        .agg(score=(pl.col("gross") * pl.col("genre_weight")).sum().cast(pl.Float64))
        .with_columns(share=pl.col("score") / pl.col("score").sum().over(keys))
    )
    return (
        shares.join(totals, on=keys)
        .select(
            pl.col("country_iso2"),
            pl.col("year").cast(pl.Int16),
            "genre",
            "family",
            "score",
            "share",
            coverage=pl.col("matched") / pl.col("total"),
            fuzzy_share=pl.col("fuzzy") / pl.col("total"),
            estimated_share=pl.lit(0.0),
            entries="entries",
        )
        .sort([*keys, "genre"])
    )


def imdb_genre_year(
    titles: pl.DataFrame, mapping: pl.DataFrame, families: pl.DataFrame
) -> pl.DataFrame:
    """Genre shares of every IMDb film per year; shorts count only before `SHORTS_UNTIL`.

    IMDb genres are mapped to TMDB genres through `mapping` (`imdb_genre`, `genre`; a null
    `genre` drops the IMDb genre). A film counts 1/n in each of its n kept genres, and films left
    without a genre drop out. `entries` is the distinct films of a year, `shorts` the short ones.
    """
    films = titles.filter(
        (pl.col("title_type") == "movie")
        | ((pl.col("title_type") == "short") & (pl.col("year") < SHORTS_UNTIL))
    )
    exploded = films.select("imdb_id", "title_type", "year", imdb_genre="genres").explode(
        "imdb_genre"
    )
    unknown = sorted(set(exploded["imdb_genre"].drop_nulls()) - set(mapping["imdb_genre"]))
    if unknown:
        raise ValueError(f"IMDb genres missing from imdb_genres.csv: {unknown}")
    rows = (
        exploded.join(mapping, on="imdb_genre", how="inner")
        .drop_nulls("genre")
        .unique(["imdb_id", "genre"], maintain_order=True)
        .with_columns(weight=1 / pl.len().over("imdb_id"))
    )
    years = rows.group_by("year").agg(
        entries=pl.col("imdb_id").n_unique(),
        shorts=pl.col("imdb_id").filter(pl.col("title_type") == "short").n_unique(),
    )
    return (
        rows.group_by("year", "genre")
        .agg(score=pl.col("weight").sum().cast(pl.Float64))
        .join(families.select("genre", "family"), on="genre", how="left")
        .with_columns(share=pl.col("score") / pl.col("score").sum().over("year"))
        .join(years, on="year")
        .select(
            pl.col("year").cast(pl.Int16), "genre", "family", "score", "share", "entries", "shorts"
        )
        .sort("year", "genre")
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
    kobis_path = paths.SCRAPED / "kobis.parquet"
    if lumiere_path.exists() or kobis_path.exists():
        countries = pl.read_csv(
            paths.REFERENCE / "countries.csv", schema_overrides={"iso_numeric": pl.String}
        )
        parts = []
        if lumiere_path.exists():
            parts.append(pl.read_parquet(lumiere_path))
        if kobis_path.exists():
            parts.append(kobis_as_lumiere(pl.read_parquet(kobis_path)))
        cinema = lumiere_country_genre(pl.concat(parts), genres, countries["iso2"])
        cinema.write_parquet(paths.INTERIM / "country_genre_lumiere.parquet")
        print(
            f"country_genre_lumiere: {cinema.height} rows, "
            f"{cinema['country_iso2'].n_unique()} markets, "
            f"years {cinema['year'].min()}-{cinema['year'].max()}"
        )
    else:
        print("lumiere.parquet and kobis.parquet not found; no cinema genre shares")

    for name, table in (
        ("production", production_country_genre(films, genres)),
        ("us", us_cinema_country_genre(films, genres)),
    ):
        table.write_parquet(paths.INTERIM / f"country_genre_{name}.parquet")
        print(
            f"country_genre_{name}: {table.height} rows, "
            f"{table['country_iso2'].n_unique()} countries, "
            f"years {table['year'].min()}-{table['year'].max()}"
        )

    imdb_path = paths.INTERIM / "imdb.parquet"
    if imdb_path.exists():
        mapping = pl.read_csv(
            paths.REFERENCE / "imdb_genres.csv", schema_overrides={"genre": pl.String}
        )
        imdb = imdb_genre_year(pl.read_parquet(imdb_path), mapping, families)
        imdb.write_parquet(paths.INTERIM / "imdb_genre_year.parquet")
        print(
            f"imdb_genre_year: {imdb.height} rows, years {imdb['year'].min()}-{imdb['year'].max()}"
        )
    else:
        print("imdb.parquet not found; no IMDb genre shares")

    coverage = out.unique(["country_iso2", "year"])["coverage"]
    print(f"film_genres: {genres.height} rows, {genres['imdb_id'].n_unique()} films")
    print(
        f"country_genre_netflix: {out.height} rows, {out['country_iso2'].n_unique()} countries, "
        f"years {out['year'].min()}-{out['year'].max()}"
    )
    print(f"coverage min {coverage.min():.3f}, median {coverage.median():.3f}")
