"""Clean the UNESCO UIS feature film survey (via DBnomics) into data/interim/unesco.parquet.

Indicator 220063 is total admissions to all feature films, 220223 admissions to national films.
UIS marks a missing value "NA"; it becomes null. ISO-3 codes map to ISO-2 through countries.csv,
codes that are not in the table (aggregates, former states) are dropped.
"""

import json

import polars as pl

from movies import paths

INDICATORS = {"220063": "admissions", "220223": "admissions_national"}


def clean(payload: dict, countries: pl.DataFrame) -> pl.DataFrame:
    """DBnomics series -> (country_iso2, year, admissions, admissions_national), sorted.

    A total of 0 is a placeholder for a country with no cinema data (BI, MH), recoded to null.
    Rows with no value are dropped; a national value above the total is dropped (impossible).
    """
    rows = [
        (s["dimensions"]["country"], int(y), INDICATORS[s["dimensions"]["indicator"]], v)
        for s in payload["series"]["docs"]
        for y, v in zip(s["period"], s["value"], strict=True)
        if v != "NA" and not (v == 0 and s["dimensions"]["indicator"] == "220063")
    ]
    long = pl.DataFrame(
        rows,
        schema={
            "iso3": pl.String,
            "year": pl.Int16,
            "measure": pl.String,
            "value": pl.Float64,
        },
        orient="row",
    )
    return (
        long.join(countries.select("iso2", "iso3"), on="iso3", how="inner")
        .pivot(on="measure", index=["iso2", "year"], values="value")
        .with_columns(
            pl.col("admissions_national").cast(pl.Float64),
            pl.col("admissions").cast(pl.Float64),
        )
        .with_columns(
            pl.when(pl.col("admissions_national") > pl.col("admissions"))
            .then(None)
            .otherwise(pl.col("admissions_national"))
            .alias("admissions_national")
        )
        .filter(pl.col("admissions").is_not_null() | pl.col("admissions_national").is_not_null())
        .select(pl.col("iso2").alias("country_iso2"), "year", "admissions", "admissions_national")
        .sort("country_iso2", "year")
    )


def run() -> None:
    payload = json.loads((paths.RAW / "unesco" / "film.json").read_text())
    countries = pl.read_csv(paths.REFERENCE / "countries.csv", infer_schema_length=0)
    tidy = clean(payload, countries)
    paths.INTERIM.mkdir(parents=True, exist_ok=True)
    tidy.write_parquet(paths.INTERIM / "unesco.parquet")
    iso3 = set(countries["iso3"].to_list())
    dropped = sorted({s["dimensions"]["country"] for s in payload["series"]["docs"]} - iso3)
    both = tidy.drop_nulls().height
    print(
        f"{tidy.height} rows, {tidy['country_iso2'].n_unique()} countries, "
        f"{tidy['year'].min()}-{tidy['year'].max()}, {both} country-years with both values; "
        f"dropped codes not in countries.csv: {dropped}"
    )
