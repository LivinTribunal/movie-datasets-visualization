"""Join stage: the films table (working subset of TMDB + Wikidata ids + RT + The Numbers).

Pure functions from frames to frames; only `run()` reads data/interim, data/scraped and
data/overrides and writes data/interim/films.parquet and netflix_titles.parquet. Every title match
carries its method and score, because fuzzy-matched values must be shown as such in the app.
"""

import polars as pl

from movies import paths
from movies.join.titles import apply_overrides, match

MIN_VOTES = 1000
NOTABLE_VOTES = 10_000
NETFLIX_MIN_VOTES = 100
NETFLIX_FUZZY_YEARS = 2  # older fuzzy candidates were mostly wrong films
_FILM_KEYS = ["imdb_id", "title", "original_title", "year", "imdb_votes"]
_NUMBERS_VALUES = [
    "budget",
    "domestic_gross",
    "worldwide_gross",
    "international_box_office",
    "opening_weekend",
    "franchise",
]


def working_subset(tmdb: pl.DataFrame) -> pl.DataFrame:
    return tmdb.filter(
        (pl.col("status") == "Released")
        & pl.col("year").is_between(1900, 2026)
        & (pl.col("imdb_votes") >= MIN_VOTES)
        & pl.col("imdb_id").is_not_null()
    ).with_columns(notable=pl.col("imdb_votes") >= NOTABLE_VOTES)


def attach_rt(films: pl.DataFrame, ids: pl.DataFrame, rt: pl.DataFrame) -> pl.DataFrame:
    """Left-join the Wikidata ids, then one RT row per film (scored rows first)."""
    picked = (
        ids.select("imdb_id", rt_id=pl.col("rt_id").str.split("|"))
        .explode("rt_id")
        .drop_nulls("rt_id")
        .join(rt, on="rt_id")
        .sort(
            [pl.col("tomatometer").is_null(), pl.col("audience_score").is_null(), "rt_id"],
        )
        .unique("imdb_id", keep="first", maintain_order=True)
        .select(
            "imdb_id",
            rt_slug="rt_id",
            tomatometer="tomatometer",
            audience_score="audience_score",
            rt_box_office_usd="box_office_usd",
            rt_release_date_theaters="release_date_theaters",
        )
    )
    return films.join(ids, on="imdb_id", how="left").join(picked, on="imdb_id", how="left")


def _key(prefix: str, id_col: str) -> pl.Expr:
    return f"{prefix}:" + pl.col(id_col).cast(pl.String)


def numbers_rows(metrics: pl.DataFrame, budgets: pl.DataFrame) -> pl.DataFrame:
    """Both Numbers tables as one frame with a `key`; rows without a year are dropped."""
    m = metrics.select(
        key=_key("metrics", "numbers_id"),
        src=pl.lit(0),
        title="title",
        year="year",
        **{c: pl.col(c) for c in _NUMBERS_VALUES},
    )
    b = budgets.select(
        key=_key("budgets", "numbers_rank"),
        src=pl.lit(1),
        title="title",
        year="year",
        budget="budget",
        domestic_gross="domestic_gross",
        worldwide_gross="worldwide_gross",
        international_box_office=pl.lit(None, dtype=pl.Float64),
        opening_weekend=pl.lit(None, dtype=pl.Float64),
        franchise=pl.lit(None, dtype=pl.String),
    )
    return pl.concat([m, b.cast({c: m.schema[c] for c in b.columns})]).drop_nulls("year")


def attach_numbers(
    films: pl.DataFrame, metrics: pl.DataFrame, budgets: pl.DataFrame, overrides: pl.DataFrame
) -> tuple[pl.DataFrame, pl.DataFrame]:
    rows = numbers_rows(metrics, budgets)
    left = rows.select("key", "title", year_min=pl.col("year") - 1, year_max=pl.col("year") + 1)
    matches = apply_overrides(match(left, films.select(_FILM_KEYS)), overrides)
    best = (
        matches.join(rows, on="key")
        .sort(
            ["imdb_id", "src", pl.col("score").fill_null(101.0), "worldwide_gross"],
            descending=[False, False, True, True],
            nulls_last=True,
        )
        .unique("imdb_id", keep="first", maintain_order=True)
        .select(
            "imdb_id",
            numbers_budget="budget",
            numbers_domestic_gross="domestic_gross",
            numbers_worldwide_gross="worldwide_gross",
            numbers_international_box_office="international_box_office",
            numbers_opening_weekend="opening_weekend",
            numbers_franchise="franchise",
            numbers_key="key",
            numbers_match="method",
            numbers_match_score="score",
        )
    )
    return films.join(best, on="imdb_id", how="left"), matches


def match_netflix(
    netflix: pl.DataFrame, tmdb: pl.DataFrame, overrides: pl.DataFrame
) -> pl.DataFrame:
    """Netflix title -> imdb_id; a film cannot predate the title's first chart week."""
    titles = netflix.group_by("title").agg(first_week=pl.col("week").min())
    left = titles.select(
        key="title", title="title", year_min=pl.lit(1900), year_max=pl.col("first_week").dt.year()
    )
    right = tmdb.filter(
        (pl.col("status") == "Released")
        & pl.col("imdb_id").is_not_null()
        & pl.col("year").is_not_null()
        & (pl.col("imdb_votes") >= NETFLIX_MIN_VOTES)
    ).select(_FILM_KEYS)
    matches = apply_overrides(match(left, right, fuzzy_years=NETFLIX_FUZZY_YEARS), overrides)
    return (
        titles.join(matches, left_on="title", right_on="key", how="left")
        .select("title", "imdb_id", "method", "score", "first_week")
        .sort("title")
    )


def _overrides(name: str) -> pl.DataFrame:
    return pl.read_csv(paths.OVERRIDES / name, infer_schema_length=0).select("key", "imdb_id")


def run() -> None:
    tmdb = pl.read_parquet(paths.INTERIM / "tmdb.parquet")
    ids = pl.read_parquet(paths.SCRAPED / "wikidata_ids.parquet")
    rt = pl.read_parquet(paths.INTERIM / "rt_clapper.parquet")
    metrics = pl.read_parquet(paths.INTERIM / "numbers_metrics.parquet")
    budgets = pl.read_parquet(paths.INTERIM / "numbers_budgets.parquet")
    netflix = pl.read_parquet(paths.INTERIM / "netflix.parquet")

    films = attach_rt(working_subset(tmdb), ids, rt)
    films, matches = attach_numbers(films, metrics, budgets, _overrides("numbers.csv"))
    titles = match_netflix(netflix, tmdb, _overrides("netflix.csv"))
    films.write_parquet(paths.INTERIM / "films.parquet")
    titles.write_parquet(paths.INTERIM / "netflix_titles.parquet")

    notable = films.filter("notable")
    print(f"films: {films.height} rows, {notable.height} notable")
    print(
        f"RT linked: {films['rt_slug'].is_not_null().sum()}, "
        f"with tomatometer: {films['tomatometer'].is_not_null().sum()}"
    )
    rows = numbers_rows(metrics, budgets)
    by_method = matches.group_by("method").len().sort("method").rows()
    print(f"Numbers rows matched (of {rows.height} with a year): {dict(by_method)}")
    print(
        f"films with a Numbers budget: {films['numbers_budget'].is_not_null().sum()}, "
        f"notable: {notable['numbers_budget'].is_not_null().sum()}"
    )
    n_by_method = titles.group_by("method").len().sort("method").rows()
    matched = titles.filter(pl.col("imdb_id").is_not_null())
    score = netflix.group_by("title").agg(total=pl.col("score").sum())
    share = score.join(matched.select("title"), on="title")["total"].sum() / score["total"].sum()
    print(
        f"Netflix titles matched (of {titles.height}): {dict(n_by_method)}; "
        f"chart score share on matched titles: {share:.1%}"
    )
    print("top unmatched Numbers rows by worldwide gross:")
    print(
        rows.join(matches.select("key"), on="key", how="anti")
        .sort("worldwide_gross", descending=True, nulls_last=True)
        .head(15)
        .select("key", "title", "year", "worldwide_gross")
    )
    print("top unmatched Netflix titles by total score:")
    print(
        score.join(matched.select("title"), on="title", how="anti")
        .sort("total", descending=True)
        .head(15)
    )
