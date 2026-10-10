from pathlib import Path

import polars as pl

from movies.clean.cpi import clean

FIXTURES = Path(__file__).parent / "fixtures"


def test_yearly_mean_and_months() -> None:
    out = clean(pl.read_csv(FIXTURES / "cpi.csv", infer_schema_length=0))
    assert out["year"].to_list() == [2000, 2001, 2002]
    assert out["cpi"].to_list() == [15.0, 40.0, 65.0]
    assert out["months"].to_list() == [2, 2, 2]


def test_dtypes() -> None:
    out = clean(pl.read_csv(FIXTURES / "cpi.csv", infer_schema_length=0))
    assert out.schema == {"year": pl.Int16, "cpi": pl.Float64, "months": pl.Int8}
