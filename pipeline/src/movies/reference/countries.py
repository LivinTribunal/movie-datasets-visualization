"""Build data/reference/countries.csv: ISO-2 key, ISO-3, numeric, name, UN M49 region, aliases."""

import polars as pl

from movies import paths

COLUMNS = [
    "iso2",
    "iso3",
    "iso_numeric",
    "name",
    "region",
    "subregion",
    "region_code",
    "subregion_code",
]


def _nullify(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(
        pl.when(pl.col(c).str.strip_chars() == "").then(None).otherwise(pl.col(c)).alias(c)
        for c in df.columns
    )


def build(iso: pl.DataFrame, extra: pl.DataFrame, aliases: pl.DataFrame) -> pl.DataFrame:
    """ISO list + extra codes + aliases -> one row per country, sorted by iso2."""
    base = iso.select(
        pl.col("alpha-2").alias("iso2"),
        pl.col("alpha-3").alias("iso3"),
        pl.col("country-code").alias("iso_numeric"),
        pl.col("name"),
        pl.col("region"),
        pl.col("sub-region").alias("subregion"),
        pl.col("region-code").alias("region_code"),
        pl.col("sub-region-code").alias("subregion_code"),
    )
    table = pl.concat([_nullify(base), _nullify(extra.select(COLUMNS))])
    table = table.with_columns(pl.col("iso_numeric").str.zfill(3))

    dup = table.filter(pl.col("iso2").is_duplicated())["iso2"].unique().to_list()
    if dup:
        raise ValueError(f"duplicate iso2: {dup}")
    unknown = aliases.filter(~pl.col("iso2").is_in(table["iso2"].implode()))["alias"].to_list()
    if unknown:
        raise ValueError(f"aliases point to unknown iso2: {unknown}")
    repeated = aliases.filter(pl.col("alias").is_duplicated())["alias"].unique().to_list()
    if repeated:
        raise ValueError(f"duplicate aliases: {repeated}")
    clash = aliases.filter(pl.col("alias").is_in(table["name"].implode()))["alias"].to_list()
    if clash:
        raise ValueError(f"aliases equal an official name: {clash}")

    joined = aliases.group_by("iso2").agg(pl.col("alias").sort().str.join("|").alias("aliases"))
    return table.join(joined, on="iso2", how="left").select([*COLUMNS, "aliases"]).sort("iso2")


def name_index(countries: pl.DataFrame) -> pl.DataFrame:
    """One row per official name and per alias: (name, iso2)."""
    official = countries.select("name", "iso2")
    alias = (
        countries.filter(pl.col("aliases").is_not_null())
        .select(pl.col("aliases").str.split("|").alias("name"), "iso2")
        .explode("name")
    )
    return pl.concat([official, alias]).unique(subset="name")


def run() -> None:
    iso = pl.read_csv(paths.RAW / "countries_iso" / "all.csv", infer_schema_length=0)
    extra = pl.read_csv(paths.REFERENCE / "country_extra.csv", infer_schema_length=0)
    aliases = pl.read_csv(paths.REFERENCE / "country_aliases.csv", infer_schema_length=0)
    out = build(iso, extra, aliases)
    out.write_csv(paths.REFERENCE / "countries.csv")
    print(f"countries.csv: {out.height} rows")
