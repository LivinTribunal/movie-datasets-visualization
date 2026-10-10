"""Clean TMDB_all_movies.csv: one typed row per film, zero sentinels recoded to null."""

from datetime import date

import polars as pl

from movies import paths
from movies.reference.countries import name_index

SNAPSHOT = date(2026, 10, 1)
MIN_BUDGET = 1000  # below this a budget is a unit error (thousands, not dollars)

TEXT = ["title", "original_title", "original_language", "status", "director", "certification_us"]
NOT_A_NAME = ["", "N/A"]


def _num(col: str) -> pl.Expr:
    return pl.col(col).cast(pl.Float64, strict=False)


def _names(col: str) -> pl.Expr:
    """ ", "-joined names -> list of names, without "" and "N/A"."""
    return (
        pl.col(col).str.split(", ").list.eval(pl.element().filter(~pl.element().is_in(NOT_A_NAME)))
    )


def _empty_to_null(expr: pl.Expr) -> pl.Expr:
    return pl.when(expr.list.len() == 0).then(None).otherwise(expr)


def _countries(raw: pl.LazyFrame, names: pl.DataFrame) -> pl.LazyFrame:
    """(row, production_countries as ISO-2 list); names without a match are dropped."""
    return (
        raw.select(pl.int_range(pl.len()).alias("row"), _names("production_countries").alias("n"))
        .explode("n")
        .join(names.lazy(), left_on="n", right_on="name", how="left", maintain_order="left")
        .group_by("row", maintain_order=True)
        .agg(pl.col("iso2").drop_nulls().alias("production_countries"))
    )


def parse(raw: pl.LazyFrame, names: pl.DataFrame) -> pl.DataFrame:
    """All-string raw scan -> typed frame, before duplicate removal."""
    budget = _num("budget")
    release = pl.col("release_date").str.to_date("%Y-%m-%d", strict=False)
    release = pl.when(release <= SNAPSHOT).then(release)
    countries = _countries(raw, names)
    return (
        raw.drop("production_countries")
        .with_row_index("row")
        .join(countries, on="row", how="left")
        .select(
            _num("id").cast(pl.Int64).alias("tmdb_id"),
            pl.col("imdb_id").str.extract(r"^(tt\d+)$", 1),
            *(pl.when(pl.col(c).str.strip_chars() != "").then(pl.col(c)).alias(c) for c in TEXT),
            release.alias("release_date"),
            release.dt.year().cast(pl.Int16).alias("year"),
            pl.when(_num("runtime") > 0).then(_num("runtime")).cast(pl.Int16).alias("runtime"),
            pl.when(budget >= MIN_BUDGET).then(budget).alias("budget"),
            ((budget > 0) & (budget < MIN_BUDGET)).alias("budget_under_1000"),
            pl.when(_num("revenue") > 0).then(_num("revenue")).alias("revenue"),
            pl.when(_num("vote_count") > 0).then(_num("vote_average")).alias("vote_average"),
            _num("vote_count").cast(pl.Int64).alias("vote_count"),
            _num("imdb_rating").alias("imdb_rating"),
            _num("imdb_votes").cast(pl.Int64).alias("imdb_votes"),
            _num("popularity").alias("popularity"),
            _empty_to_null(_names("genres")).alias("genres"),
            _empty_to_null(pl.col("production_countries")).alias("production_countries"),
        )
        .collect()
    )


def dedup(df: pl.DataFrame) -> pl.DataFrame:
    """One row per imdb_id (most imdb_votes, then vote_count, lowest tmdb_id), sorted by tmdb_id."""
    ranked = df.sort(
        ["imdb_votes", "vote_count", "tmdb_id"],
        descending=[True, True, False],
        nulls_last=True,
    )
    keyed = ranked.filter(pl.col("imdb_id").is_not_null()).unique(
        subset="imdb_id", keep="first", maintain_order=True
    )
    unkeyed = ranked.filter(pl.col("imdb_id").is_null())
    return pl.concat([keyed, unkeyed]).sort("tmdb_id")


def clean(raw: pl.LazyFrame, names: pl.DataFrame) -> pl.DataFrame:
    return dedup(parse(raw, names))


def run() -> None:
    raw = pl.scan_csv(paths.RAW / "tmdb" / "TMDB_all_movies.csv", infer_schema=False)
    countries = pl.read_csv(paths.REFERENCE / "countries.csv", infer_schema_length=0)
    names = name_index(countries)

    parsed = parse(raw, names)
    out = dedup(parsed)
    zero = raw.select((_num("budget") == 0).sum()).collect().item()
    unmatched = (
        raw.select(_names("production_countries").alias("n"))
        .explode("n")
        .filter(pl.col("n").is_not_null() & ~pl.col("n").is_in(names["name"].implode()))
        .group_by("n")
        .len()
        .sort("len", descending=True)
        .collect()
    )

    paths.INTERIM.mkdir(parents=True, exist_ok=True)
    out.write_parquet(paths.INTERIM / "tmdb.parquet")
    print(f"tmdb: {out.height} rows, {out['imdb_id'].count()} with imdb_id")
    print(f"duplicate imdb_ids dropped: {parsed.height - out.height}")
    print(f"budget nulled: {zero} zero, {int(out['budget_under_1000'].sum())} under {MIN_BUDGET}")
    for name, n in unmatched.iter_rows():
        print(f"unmatched country {name!r}: {n} films")
