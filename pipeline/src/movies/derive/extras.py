"""Derive extras: story source, age rating, studio, opening weekend, theatres, legs, home video
and Oscars, one row per film, from the TMDB columns, The Numbers metrics and Wikidata.

Story source reads The Numbers `Source` first, else the first mapped TMDB keyword; neither says
anything gives null, never `original`. Opening weekend and home video are inflated to 2025 USD
with the same CPI rule as `money.py`. The Numbers values count only for a film matched to a
metrics row (`numbers_key` starting `metrics:`). Money is never imputed.
"""

import polars as pl

from movies import paths
from movies.derive.money import BASE_YEAR

AGE_RATINGS = ["G", "PG", "PG-13", "R", "NC-17", "NR"]
_RATING_MAP = {r: r for r in AGE_RATINGS} | {"Not Rated": "NR"}
_IDS = ("csfd_id", "filmaffinity_id", "allocine_id", "douban_id")
DETAIL_COLUMNS = ["overview", "cast", "writers", "companies", "qid", *_IDS]
_NUMBERS_FIVE = ("opening_usd", "theaters", "legs", "video_usd")


def _rating(col: str) -> pl.Expr:
    return pl.col(col).str.strip_chars().replace_strict(_RATING_MAP, default=None)


def _story(films: pl.DataFrame, story_map: pl.DataFrame) -> pl.DataFrame:
    """Add `story_source` and `story_source_src` from the Numbers label, else TMDB keywords."""
    numbers = {
        label: cat
        for origin, label, cat in story_map.select("origin", "label", "category").iter_rows()
        if origin == "numbers"
    }
    tmdb = [
        (label, cat)
        for origin, label, cat in story_map.select("origin", "label", "category").iter_rows()
        if origin == "tmdb"
    ]
    from_numbers = pl.col("numbers_source").str.strip_chars().replace_strict(numbers, default=None)
    from_tmdb = pl.coalesce(
        pl.when(pl.col("keywords").list.contains(label)).then(pl.lit(cat)) for label, cat in tmdb
    )
    return films.with_columns(_numbers=from_numbers, _tmdb=from_tmdb.cast(pl.String)).with_columns(
        story_source=pl.coalesce("_numbers", "_tmdb"),
        story_source_src=pl.when(pl.col("_numbers").is_not_null())
        .then(pl.lit("numbers"))
        .when(pl.col("_tmdb").is_not_null())
        .then(pl.lit("tmdb")),
    )


def _studio(films: pl.DataFrame, studios: pl.DataFrame) -> pl.DataFrame:
    """Add `studio`: group of the first listed company, `independent`, or null."""
    first = (
        films.select("imdb_id", "companies")
        .explode("companies")
        .join(studios.select("company", "studio"), left_on="companies", right_on="company")
        .unique("imdb_id", keep="first", maintain_order=True)
        .select("imdb_id", "studio")
    )
    return films.join(first, on="imdb_id", how="left").with_columns(
        studio=pl.when(pl.col("companies").list.len() > 0)
        .then(pl.col("studio").fill_null("independent"))
        .otherwise(None)
    )


def extras(
    films: pl.DataFrame,
    metrics: pl.DataFrame,
    wikidata_extra: pl.DataFrame | None,
    cpi: pl.DataFrame,
    story_map: pl.DataFrame,
    studios: pl.DataFrame,
) -> pl.DataFrame:
    """One row per `imdb_id` in `films`; columns as in the extra-data spec §2."""
    cpi_base = cpi.filter(pl.col("year") == BASE_YEAR)["cpi"].item()
    cpi_year = cpi.select("year", pl.col("cpi").alias("cpi_year"))
    m = metrics.select(
        pl.col("numbers_id").cast(pl.Int64),
        numbers_source=pl.col("source"),
        mpaa_rating=pl.col("mpaa_rating"),
        opening_usd=pl.col("opening_weekend").cast(pl.Float64),
        theaters=pl.col("theaters_max").cast(pl.Int32),
        legs=pl.col("legs").cast(pl.Float64),
        video_usd=pl.col("video_sales").cast(pl.Float64),
    )
    df = (
        films.select(
            "imdb_id",
            "year",
            "certification_us",
            "keywords",
            "companies",
            "cast",
            "writers",
            "overview",
            "qid",
            "numbers_match",
            numbers_id=pl.when(pl.col("numbers_key").str.starts_with("metrics:")).then(
                pl.col("numbers_key").str.slice(len("metrics:")).cast(pl.Int64, strict=False)
            ),
        )
        .join(m, on="numbers_id", how="left")
        .join(cpi_year, on="year", how="left")
    )
    df = _studio(_story(df, story_map), studios)
    if wikidata_extra is None:
        wd = pl.DataFrame(
            schema={
                "imdb_id": pl.String,
                "wd_qid": pl.String,
                "oscar_wins": pl.Int16,
                "oscar_noms": pl.Int16,
                **dict.fromkeys(_IDS, pl.String),
            }
        )
    else:
        wd = wikidata_extra.group_by("imdb_id", maintain_order=True).agg(
            pl.col("qid").drop_nulls().sort().first().alias("wd_qid"),
            pl.col("oscar_wins").max(),
            pl.col("oscar_noms").max(),
            *(pl.col(c).drop_nulls().sort().first() for c in _IDS),
        )
    df = df.join(wd, on="imdb_id", how="left").with_columns(qid=pl.coalesce("qid", "wd_qid"))
    # a film with a QID but no Academy Award statement has 0; without a QID, or without the
    # Wikidata file, the count is unknown
    known = pl.col("qid").is_not_null() & (wikidata_extra is not None)
    df = df.with_columns(
        oscar_wins=pl.when(known).then(pl.col("oscar_wins").fill_null(0)),
        oscar_noms=pl.when(known).then(pl.col("oscar_noms").fill_null(0)),
        opening_usd2025=pl.col("opening_usd") * cpi_base / pl.col("cpi_year"),
        video_usd2025=pl.col("video_usd") * cpi_base / pl.col("cpi_year"),
        age_rating=pl.coalesce(_rating("certification_us"), _rating("mpaa_rating")),
        companies=pl.col("companies").list.head(3).list.join(", "),
        cast=pl.col("cast").list.join(", "),
        writers=pl.col("writers").list.join(", "),
    )
    df = df.with_columns(
        numbers_fuzzy=(
            (pl.col("numbers_match") == "fuzzy")
            & pl.any_horizontal(pl.col(c).is_not_null() for c in _NUMBERS_FIVE)
        ).fill_null(False)
    )
    return df.select(
        "imdb_id",
        "story_source",
        "story_source_src",
        "age_rating",
        "studio",
        "opening_usd",
        "opening_usd2025",
        "theaters",
        "legs",
        "video_usd2025",
        "numbers_fuzzy",
        "oscar_wins",
        "oscar_noms",
        *DETAIL_COLUMNS,
    )


def run() -> None:
    films = pl.read_parquet(paths.INTERIM / "films.parquet")
    metrics = pl.read_parquet(paths.INTERIM / "numbers_metrics.parquet")
    cpi = pl.read_parquet(paths.INTERIM / "cpi.parquet")
    story_map = pl.read_csv(paths.REFERENCE / "story_sources.csv")
    studios = pl.read_csv(paths.REFERENCE / "studios.csv")
    path = paths.SCRAPED / "wikidata_extra.parquet"
    wikidata_extra = pl.read_parquet(path) if path.exists() else None
    if wikidata_extra is None:
        print(f"{path.name} not found; Oscar counts and external ids stay null")
    out = extras(films, metrics, wikidata_extra, cpi, story_map, studios)
    out.write_parquet(paths.INTERIM / "extras.parquet")
    print(f"films: {out.height}")
    for col in ("story_source", "age_rating", "studio", "opening_usd", "theaters", "oscar_noms"):
        print(f"{col}: {out[col].count()} films")
    print(f"story source by origin: {dict(out['story_source_src'].value_counts().iter_rows())}")
    print(f"numbers_fuzzy: {int(out['numbers_fuzzy'].sum())}")
