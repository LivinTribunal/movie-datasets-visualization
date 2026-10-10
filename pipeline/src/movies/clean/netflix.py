"""Clean the Netflix weekly Top 10 (all-weeks-countries.tsv) into data/interim/netflix.parquet.

Films only (TV is out of scope). Weeks after the snapshot date are dropped. `score` is the
rank-weighted chart score: 11 - weekly_rank, so rank 1 scores 10 and rank 10 scores 1.
"""

from datetime import date

import polars as pl

from movies import paths

SNAPSHOT = date(2026, 9, 27)


def clean(raw: pl.DataFrame, countries: pl.DataFrame) -> pl.DataFrame:
    """Raw TSV rows -> one row per (country, week, rank) for films up to the snapshot."""
    unknown = sorted(set(raw["country_iso2"].unique().to_list()) - set(countries["iso2"].to_list()))
    if unknown:
        raise ValueError(f"country_iso2 not in countries table: {unknown}")
    return (
        raw.filter(pl.col("category") == "Films")
        .select(
            pl.col("country_iso2"),
            pl.col("week").str.to_date("%Y-%m-%d"),
            pl.col("weekly_rank").cast(pl.Int8),
            pl.col("show_title").alias("title"),
            pl.col("cumulative_weeks_in_top_10").cast(pl.Int16).alias("cumulative_weeks"),
        )
        .filter(pl.col("week") <= SNAPSHOT)
        .with_columns((11 - pl.col("weekly_rank")).cast(pl.Int8).alias("score"))
        .sort("week", "country_iso2", "weekly_rank")
    )


def run() -> None:
    raw = pl.read_csv(
        paths.RAW / "netflix" / "all-weeks-countries.tsv",
        separator="\t",
        quote_char=None,
        infer_schema_length=0,
    )
    countries = pl.read_csv(paths.REFERENCE / "countries.csv", infer_schema_length=0)
    tidy = clean(raw, countries)
    paths.INTERIM.mkdir(parents=True, exist_ok=True)
    tidy.write_parquet(paths.INTERIM / "netflix.parquet")
    print(
        f"{tidy.height} rows, weeks {tidy['week'].min()}..{tidy['week'].max()}, "
        f"{tidy['country_iso2'].n_unique()} countries"
    )
