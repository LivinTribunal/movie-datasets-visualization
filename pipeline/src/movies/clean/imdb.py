"""Clean the IMDb title.basics dump into data/interim/imdb.parquet.

The file is the IMDb non-commercial dataset downloaded 2026-11-17. It is read lazily because the
gzip holds every title. Only movies and shorts that are not adult and have a start year in
1900-2026 are kept; `genres` is the list of IMDb genre names (empty when IMDb has none).
"""

import polars as pl

from movies import paths


def clean(raw: pl.LazyFrame) -> pl.LazyFrame:
    """Raw title.basics rows -> one row per movie or short, sorted by `imdb_id`."""
    return (
        raw.filter(pl.col("titleType").is_in(["movie", "short"]) & (pl.col("isAdult") == "0"))
        .select(
            imdb_id=pl.col("tconst"),
            title_type=pl.col("titleType"),
            year=pl.col("startYear").cast(pl.Int16, strict=False),
            genres=pl.col("genres").str.split(",").fill_null([]),
        )
        .filter(pl.col("year").is_between(1900, 2026))
        .sort("imdb_id")
    )


def run() -> None:
    raw = pl.scan_csv(
        paths.RAW / "imdb" / "title.basics.tsv.gz",
        separator="\t",
        quote_char=None,
        null_values="\\N",
        infer_schema=False,
    )
    tidy = clean(raw).collect()
    paths.INTERIM.mkdir(parents=True, exist_ok=True)
    tidy.write_parquet(paths.INTERIM / "imdb.parquet")
    counts = tidy.group_by("title_type").len().sort("title_type")
    print(f"{tidy.height} rows, " + ", ".join(f"{t} {n}" for t, n in counts.iter_rows()))
