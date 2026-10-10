"""Clean The Numbers: budgets/revenues list and the top-movies metrics table."""

from datetime import date

import polars as pl

from movies import paths

# the metrics file read 2-digit years ('15-Dec-39') as 20xx; nothing is released after the snapshot
SNAPSHOT = date(2026, 10, 1)

MONEY = {
    "budget",
    "domestic_gross",
    "worldwide_gross",
    "international_box_office",
    "opening_weekend",
}


def parse_usd(expr: pl.Expr) -> pl.Expr:
    """'$1,234' or '1234.0' -> 1234.0; zero means unknown -> null."""
    num = expr.cast(pl.String).str.replace_all(r"[$,\s]", "").cast(pl.Float64, strict=False)
    return pl.when(num == 0).then(None).otherwise(num).alias(expr.meta.output_name())


def _text(col: str) -> pl.Expr:
    s = pl.col(col).str.strip_chars()
    return pl.when(s == "").then(None).otherwise(s)


def _dates(col: str, fmt: str | None, *, fix_century: bool = False) -> list[pl.Expr]:
    """release_date and year; the year falls back to a 4-digit year in the raw string.

    With `fix_century`, a date after SNAPSHOT is moved back 100 years.
    """
    day = pl.col(col).str.to_date(fmt, strict=False)
    if fix_century:
        day = pl.when(day > SNAPSHOT).then(day.dt.offset_by("-100y")).otherwise(day)
    year = day.dt.year().fill_null(pl.col(col).str.extract(r"\b(\d{4})\b", 1).cast(pl.Int32))
    return [day.alias("release_date"), year.cast(pl.Int16).alias("year")]


def clean_budgets(raw: pl.DataFrame) -> pl.DataFrame:
    return raw.select(
        pl.col("Number").str.replace_all(",", "").cast(pl.Int32).alias("numbers_rank"),
        _text("Movie Name").alias("title"),
        *_dates("Release Date", "%b %d, %Y"),
        parse_usd(pl.col("Budget")).alias("budget"),
        parse_usd(pl.col("Domestic Gross")).alias("domestic_gross"),
        parse_usd(pl.col("Worldwide Gross")).alias("worldwide_gross"),
    )


def clean_metrics(raw: pl.DataFrame) -> pl.DataFrame:
    return raw.select(
        pl.col("id").str.replace_all(",", "").cast(pl.Int32).alias("numbers_id"),
        _text("Movie Name").alias("title"),
        *_dates("Release Date", "%Y-%m-%d", fix_century=True),
        parse_usd(pl.col("Production Budget (USD)")).alias("budget"),
        parse_usd(pl.col("Domestic Gross (USD)")).alias("domestic_gross"),
        parse_usd(pl.col("Worldwide Gross (USD)")).alias("worldwide_gross"),
        parse_usd(pl.col("International Box Office (USD)")).alias("international_box_office"),
        parse_usd(pl.col("Opening Weekend (USD)")).alias("opening_weekend"),
        _text("MPAA Rating").alias("mpaa_rating"),
        _text("Running Time (minutes)").cast(pl.Int16, strict=False).alias("runtime"),
        _text("Franchise").alias("franchise"),
        _text("Source").alias("source"),
        _text("Genre").alias("genre"),
        _text("Production Method").alias("production_method"),
        _text("Creative Type").alias("creative_type"),
        _text("Movie URL").alias("url"),
    )


def run() -> None:
    paths.INTERIM.mkdir(parents=True, exist_ok=True)
    jobs = [
        (
            "numbers_budgets",
            paths.RAW / "numbers_budgets" / "movie_budgets_and_revenues.csv",
            clean_budgets,
        ),
        (
            "numbers_metrics",
            paths.RAW / "numbers_metrics" / "Top Movies (Cleaned Data).csv",
            clean_metrics,
        ),
    ]
    for name, path, fn in jobs:
        out = fn(pl.read_csv(path, infer_schema=False))
        out.write_parquet(paths.INTERIM / f"{name}.parquet")
        money = {c: out[c].count() for c in out.columns if c in MONEY}
        print(f"{name}: {out.height} rows, non-null money {money}")
