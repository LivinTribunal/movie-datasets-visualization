"""Clean the Rotten Tomatoes (Clapper) movie list: one row per RT film, typed, scores 0-100."""

import polars as pl

from movies import paths

SCORES = ["tomatometer", "audience_score", "box_office_usd"]
_SUFFIX = {"K": 1e3, "M": 1e6, "B": 1e9}


def _text(col: str) -> pl.Expr:
    s = pl.col(col).str.strip_chars()
    return pl.when(s == "").then(None).otherwise(s)


def _box_office(col: str) -> pl.Expr:
    s = pl.col(col).str.strip_chars().str.replace_all(",", "")
    num = s.str.extract(r"^\$?(\d+(?:\.\d+)?)[KMB]?$", 1).cast(pl.Float64, strict=False)
    mult = s.str.extract(r"([KMB])$", 1).replace_strict(
        _SUFFIX, default=1.0, return_dtype=pl.Float64
    )
    return num * mult


def clean(raw: pl.DataFrame) -> pl.DataFrame:
    """Raw all-string frame -> tidy frame, one row per `id` (the fullest row wins)."""
    df = raw.select(
        pl.col("id"),
        ("m/" + pl.col("id")).alias("rt_id"),
        _text("title").alias("title"),
        _text("tomatoMeter").cast(pl.Int8, strict=False).alias("tomatometer"),
        _text("audienceScore").cast(pl.Int8, strict=False).alias("audience_score"),
        _text("rating").alias("rating"),
        _text("releaseDateTheaters").str.to_date(strict=False).alias("release_date_theaters"),
        _text("releaseDateStreaming").str.to_date(strict=False).alias("release_date_streaming"),
        _text("runtimeMinutes").cast(pl.Int16, strict=False).alias("runtime"),
        _text("genre").str.split(", ").alias("genres"),
        _text("originalLanguage").alias("original_language"),
        _text("director").alias("director"),
        _text("distributor").alias("distributor"),
        _box_office("boxOffice").alias("box_office_usd"),
    ).with_row_index("_idx")
    filled = pl.sum_horizontal(pl.col(c).is_not_null() for c in SCORES)
    return (
        df.sort(filled, "_idx", descending=[True, False])
        .unique(subset="id", keep="first", maintain_order=True)
        .sort("_idx")
        .drop("id", "_idx")
    )


def run() -> None:
    raw = pl.read_csv(paths.RAW / "rt_clapper" / "rotten_tomatoes_movies.csv", infer_schema=False)
    out = clean(raw)
    paths.INTERIM.mkdir(parents=True, exist_ok=True)
    out.write_parquet(paths.INTERIM / "rt_clapper.parquet")
    print(f"rt_clapper: {out.height} rows, {raw.height - out.height} duplicate ids dropped")
    for c in SCORES:
        print(f"  {c}: {out[c].count()} non-null")
