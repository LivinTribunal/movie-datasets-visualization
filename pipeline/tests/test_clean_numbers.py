import datetime as dt
from pathlib import Path

import polars as pl

from movies.clean.numbers import clean_budgets, clean_metrics, parse_usd

FIXTURES = Path(__file__).parent / "fixtures"


def _read(name: str) -> pl.DataFrame:
    return pl.read_csv(FIXTURES / name, infer_schema=False)


def test_parse_usd() -> None:
    s = pl.DataFrame({"v": ["$1,395,316,979", "$0", "1234.0", "0", "", None]})
    out = s.select(parse_usd(pl.col("v")))["v"].to_list()
    assert out == [1_395_316_979.0, None, 1234.0, None, None, None]


def test_budgets_dates_and_money() -> None:
    out = clean_budgets(_read("numbers_budgets_sample.csv"))
    first = out.row(0, named=True)
    assert first["release_date"] == dt.date(2015, 4, 22)
    assert first["year"] == 2015
    assert first["worldwide_gross"] == 1_395_316_979.0
    assert first["numbers_rank"] == 6
    assert out["numbers_rank"].to_list()[-1] == 1000  # "1,000" in the raw file
    year_only = out.filter(pl.col("title") == "Year Only").row(0, named=True)
    assert year_only["release_date"] is None
    assert year_only["year"] == 2010
    assert year_only["domestic_gross"] is None
    unknown = out.filter(pl.col("title") == "Mystery Film").row(0, named=True)
    assert unknown["release_date"] is None
    assert unknown["year"] is None
    assert unknown["budget"] is None


def test_metrics_zero_is_null() -> None:
    out = clean_metrics(_read("numbers_metrics_sample.csv"))
    tiny = out.filter(pl.col("title") == "Tiny Film").row(0, named=True)
    assert tiny["budget"] is None
    assert tiny["opening_weekend"] is None
    assert tiny["mpaa_rating"] is None
    assert tiny["runtime"] is None
    first = out.row(0, named=True)
    assert first["opening_weekend"] == 247_966_675.0
    assert first["runtime"] == 136
    assert first["release_date"] == dt.date(2015, 12, 16)
    gwtw = out.filter(pl.col("title") == "Gone with the Wind").row(0, named=True)
    assert gwtw["numbers_id"] == 5201
    assert gwtw["release_date"] == dt.date(1939, 12, 15)  # raw 2039: a 2-digit year read as 20xx
    assert gwtw["year"] == 1939
    undated = out.filter(pl.col("title") == "Undated Film").row(0, named=True)
    assert undated["year"] is None
