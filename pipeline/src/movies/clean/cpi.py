"""Clean FRED CPIAUCSL (monthly, USD CPI-U) into a yearly mean in data/interim/cpi.parquet.

`months` is the number of months present in the year, so a partial year is visible.
"""

import polars as pl

from movies import paths


def clean(raw: pl.DataFrame) -> pl.DataFrame:
    """Monthly observations -> one row per year: mean CPI and months present."""
    return (
        raw.with_columns(pl.col("observation_date").str.to_date("%Y-%m-%d"))
        .group_by(pl.col("observation_date").dt.year().cast(pl.Int16).alias("year"))
        .agg(
            pl.col("CPIAUCSL").cast(pl.Float64).mean().alias("cpi"),
            pl.len().cast(pl.Int8).alias("months"),
        )
        .sort("year")
    )


def run() -> None:
    raw = pl.read_csv(paths.RAW / "cpi" / "CPIAUCSL.csv", infer_schema_length=0)
    tidy = clean(raw)
    paths.INTERIM.mkdir(parents=True, exist_ok=True)
    tidy.write_parquet(paths.INTERIM / "cpi.parquet")
    print(f"{tidy.height} years, {tidy['year'].min()}..{tidy['year'].max()}")
