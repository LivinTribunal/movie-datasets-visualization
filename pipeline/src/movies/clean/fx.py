"""Clean World Bank PA.NUS.FCRF into data/interim/fx.parquet.

Values are "official exchange rate, LCU per US$, period average". Euro members are reported
in euros for all years (the derive stage deals with that). Aggregates (AFE, WLD, ...) and rows
with no value are dropped.
"""

import json

import polars as pl

from movies import paths


def clean(rows: list[dict], countries: pl.DataFrame) -> pl.DataFrame:
    """API rows -> (iso2, year, lcu_per_usd), countries only, non-null values only."""
    raw = pl.DataFrame(
        {
            "iso3": [r["countryiso3code"] for r in rows],
            "year": [r["date"] for r in rows],
            "value": [r["value"] for r in rows],
        },
        schema={"iso3": pl.String, "year": pl.String, "value": pl.Float64},
    )
    return (
        raw.join(countries.select("iso2", "iso3"), on="iso3", how="inner")
        .filter(pl.col("value").is_not_null())
        .select(
            "iso2",
            pl.col("year").cast(pl.Int16),
            pl.col("value").alias("lcu_per_usd"),
        )
        .sort("iso2", "year")
    )


def run() -> None:
    _meta, rows = json.loads((paths.RAW / "fx" / "PA.NUS.FCRF.json").read_text())
    countries = pl.read_csv(paths.REFERENCE / "countries.csv", infer_schema_length=0)
    tidy = clean(rows, countries)
    paths.INTERIM.mkdir(parents=True, exist_ok=True)
    tidy.write_parquet(paths.INTERIM / "fx.parquet")
    iso3 = set(countries["iso3"].to_list())
    aggregates = sum(1 for r in rows if r["countryiso3code"] not in iso3)
    print(
        f"{tidy.height} rows kept, {tidy['iso2'].n_unique()} countries, "
        f"{aggregates} aggregate rows dropped"
    )
