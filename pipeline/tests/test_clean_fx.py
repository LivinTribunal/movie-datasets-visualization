import json
from pathlib import Path

import polars as pl

from movies.clean.fx import clean

FIXTURES = Path(__file__).parent / "fixtures"
COUNTRIES = pl.DataFrame({"iso2": ["CZ", "SK"], "iso3": ["CZE", "SVK"]})


def _rows() -> list[dict]:
    return json.loads((FIXTURES / "fx.json").read_text())[1]


def test_drops_aggregates_and_nulls_maps_iso3() -> None:
    out = clean(_rows(), COUNTRIES)
    assert out.rows() == [("CZ", 2024, 23.3), ("SK", 2023, 0.92)]


def test_dtypes() -> None:
    out = clean(_rows(), COUNTRIES)
    assert out.schema == {"iso2": pl.String, "year": pl.Int16, "lcu_per_usd": pl.Float64}
