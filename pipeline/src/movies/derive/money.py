"""Derive money: one row per film with budget and revenue from the first source that has them.

Budget order: The Numbers, TMDB, Wikidata. Revenue order: The Numbers worldwide gross, TMDB,
Wikidata box office. Money is never imputed: a missing value, a missing FX rate or a missing CPI
year gives null. Converted (`*_usd`) and inflation-adjusted (`*_usd2025`) values keep the nominal
amount and currency beside them, because the app must show transformed data as such.
"""

import polars as pl

from movies import paths

WORLDWIDE_QID = "Q13780930"
DISAGREE_RATIO = 1.25
MIN_ROI_BUDGET = 100_000
BASE_YEAR = 2025
# below these a value is a unit error or a re-release gross, not the film's money
MIN_BUDGET = 1_000
MIN_REVENUE = 10_000
_FLOOR = {"budget": MIN_BUDGET, "revenue": MIN_REVENUE}
# (field, The Numbers column, TMDB column, Wikidata property)
_FIELDS = (
    ("budget", "numbers_budget", "budget", "budget"),
    ("revenue", "numbers_worldwide_gross", "revenue", "box_office"),
)


def wikidata_pick(money: pl.DataFrame, currencies: pl.DataFrame) -> pl.DataFrame:
    """One money statement per (imdb_id, property): USD first, preferred, latest, largest."""
    codes = currencies.select("currency_qid", currency="code")
    return (
        money.join(codes, left_on="unit_qid", right_on="currency_qid", how="inner")
        .filter(
            (pl.col("property") != "box_office")
            | pl.col("place_qid").is_null()
            | (pl.col("place_qid") == WORLDWIDE_QID)
        )
        .filter(
            pl.col("amount")
            >= pl.when(pl.col("property") == "budget").then(MIN_BUDGET).otherwise(MIN_REVENUE)
        )
        .sort(
            [
                pl.col("currency") != "USD",
                pl.col("rank") != "preferred",
                pl.col("point_in_time"),
                pl.col("amount"),
            ],
            descending=[False, False, True, True],
            nulls_last=True,
        )
        .unique(["imdb_id", "property"], keep="first", maintain_order=True)
        .select("imdb_id", "property", "amount", "currency")
    )


def to_usd(df: pl.DataFrame, col: str, currencies: pl.DataFrame, fx: pl.DataFrame) -> pl.DataFrame:
    """Add `<col>_usd` = `<col>` / lcu_per_usd for `<col>_currency` at the film's `year`.

    USD stays as is. Null outside the currency's valid years or without an FX row.
    """
    cur = f"{col}_currency"
    cur_tbl = currencies.select(pl.col("code").alias(cur), "fx_iso2", "valid_from", "valid_to")
    fx_tbl = fx.select(pl.col("iso2").alias("fx_iso2"), "year", "lcu_per_usd")
    joined = df.join(cur_tbl, on=cur, how="left").join(fx_tbl, on=["fx_iso2", "year"], how="left")
    in_years = (pl.col("valid_from").is_null() | (pl.col("year") >= pl.col("valid_from"))) & (
        pl.col("valid_to").is_null() | (pl.col("year") <= pl.col("valid_to"))
    )
    usd = (
        pl.when(pl.col(cur) == "USD")
        .then(pl.col(col))
        .when(in_years)
        .then(pl.col(col) / pl.col("lcu_per_usd"))
    )
    return joined.with_columns(usd.alias(f"{col}_usd")).drop(
        "fx_iso2", "valid_from", "valid_to", "lcu_per_usd"
    )


def source_values(
    films: pl.DataFrame, wiki: pl.DataFrame, currencies: pl.DataFrame, fx: pl.DataFrame
) -> pl.DataFrame:
    """Per film, each source's budget and revenue; values under the floor become null.

    `drop_<source column>` flags the values the floor removed. A Wikidata value that cannot be
    converted to USD is kept (nominal only).
    """
    picked = wikidata_pick(wiki, currencies)
    df = films.select(
        "imdb_id",
        "year",
        *[pl.col(num) for _, num, _, _ in _FIELDS],
        *[pl.col(tmdb).alias(f"tmdb_{field}") for field, _, tmdb, _ in _FIELDS],
    )
    for field, num, _, prop in _FIELDS:
        one = picked.filter(pl.col("property") == prop).select(
            "imdb_id",
            pl.col("amount").alias(f"wiki_{field}"),
            pl.col("currency").alias(f"wiki_{field}_currency"),
        )
        df = df.join(one, on="imdb_id", how="left")
        wiki_col, floor = f"wiki_{field}", _FLOOR[field]
        df = to_usd(df, wiki_col, currencies, fx)
        small = {
            num: pl.col(num) < floor,
            f"tmdb_{field}": pl.col(f"tmdb_{field}") < floor,
            wiki_col: pl.col(f"{wiki_col}_usd") < floor,
        }
        df = df.with_columns(
            *[expr.fill_null(False).alias(f"drop_{c}") for c, expr in small.items()]
        ).with_columns(
            *[pl.when(pl.col(f"drop_{c}")).then(None).otherwise(pl.col(c)).alias(c) for c in small],
            *[
                pl.when(pl.col(f"drop_{wiki_col}")).then(None).otherwise(pl.col(c)).alias(c)
                for c in (f"{wiki_col}_currency", f"{wiki_col}_usd")
            ],
        )
    return df


def money(
    films: pl.DataFrame,
    wiki: pl.DataFrame,
    currencies: pl.DataFrame,
    fx: pl.DataFrame,
    cpi: pl.DataFrame,
) -> pl.DataFrame:
    """One row per films row: value, currency, src, usd, usd2025 and a disagreement flag."""
    df = source_values(films, wiki, currencies, fx)
    cpi_base = cpi.filter(pl.col("year") == BASE_YEAR)["cpi"].item()
    cpi_tbl = cpi.select("year", pl.col("cpi").alias("cpi_year"))
    for field, num, _, _ in _FIELDS:
        tmdb, wiki_col = f"tmdb_{field}", f"wiki_{field}"
        df = df.with_columns(
            pl.coalesce(num, tmdb, wiki_col).alias(field),
            pl.when(pl.col(num).is_not_null() | pl.col(tmdb).is_not_null())
            .then(pl.lit("USD"))
            .otherwise(pl.col(f"{wiki_col}_currency"))
            .alias(f"{field}_currency"),
            pl.when(pl.col(num).is_not_null())
            .then(pl.lit("numbers"))
            .when(pl.col(tmdb).is_not_null())
            .then(pl.lit("tmdb"))
            .when(pl.col(wiki_col).is_not_null())
            .then(pl.lit("wikidata"))
            .alias(f"{field}_src"),
        )
        df = to_usd(df, field, currencies, fx)
        usd = [pl.col(num), pl.col(tmdb), pl.col(f"{wiki_col}_usd")]
        df = (
            df.join(cpi_tbl, on="year", how="left")
            .with_columns(
                (pl.col(f"{field}_usd") * cpi_base / pl.col("cpi_year")).alias(f"{field}_usd2025"),
                (
                    (pl.concat_list(usd).list.drop_nulls().list.len() >= 2)
                    & (pl.max_horizontal(usd) > DISAGREE_RATIO * pl.min_horizontal(usd))
                ).alias(f"{field}_disagree"),
            )
            .drop("cpi_year")
        )

    return df.select(
        "imdb_id",
        *[
            f"{field}{suffix}"
            for field, _, _, _ in _FIELDS
            for suffix in ("", "_currency", "_src", "_usd", "_usd2025")
        ],
        "budget_disagree",
        "revenue_disagree",
        profit_usd2025=pl.col("revenue_usd2025") - pl.col("budget_usd2025"),
        roi=pl.when(pl.col("budget_usd") >= MIN_ROI_BUDGET).then(
            pl.col("revenue_usd") / pl.col("budget_usd")
        ),
    )


def run() -> None:
    films = pl.read_parquet(paths.INTERIM / "films.parquet")
    wiki = pl.read_parquet(paths.SCRAPED / "wikidata_money.parquet")
    currencies = pl.read_csv(
        paths.REFERENCE / "currencies.csv",
        schema_overrides={"valid_from": pl.Int16, "valid_to": pl.Int16},
    )
    fx = pl.read_parquet(paths.INTERIM / "fx.parquet")
    cpi = pl.read_parquet(paths.INTERIM / "cpi.parquet")
    unknown = wiki.filter(~pl.col("unit_qid").is_in(currencies["currency_qid"]))
    top = unknown["unit_qid"].value_counts(sort=True).head(10)
    print(
        f"wikidata statements in a unit not in currencies.csv, by unit_qid: {dict(top.iter_rows())}"
    )
    out = money(films, wiki, currencies, fx, cpi)
    src = source_values(films, wiki, currencies, fx)
    out.write_parquet(paths.INTERIM / "money.parquet")

    joined = out.join(films.select("imdb_id", "notable"), on="imdb_id")
    print(f"films: {out.height} ({joined['notable'].sum()} notable)")
    for field, num, _, _ in _FIELDS:
        wiki = f"wiki_{field}"
        for label, sub in (("all", joined), ("notable", joined.filter(pl.col("notable")))):
            counts = sub[f"{field}_src"].value_counts().sort(f"{field}_src")
            print(f"{field} src ({label}): {dict(counts.iter_rows())}")
        converted = out.filter(pl.col(f"{field}_currency") != "USD")
        print(
            f"{field} non-USD: {converted.height}, converted to USD: "
            f"{converted[f'{field}_usd'].is_not_null().sum()}"
        )
        dropped = {
            name: int(src[f"drop_{col}"].sum())
            for name, col in (("numbers", num), ("tmdb", f"tmdb_{field}"), ("wikidata", wiki))
        }
        print(f"{field} values dropped by the floor: {dropped}")
        print(f"{field} sources disagree: {out[f'{field}_disagree'].sum()}")
    print(f"films with ROI: {out['roi'].is_not_null().sum()}")
