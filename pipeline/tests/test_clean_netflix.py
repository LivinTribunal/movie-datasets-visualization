from datetime import date
from pathlib import Path

import polars as pl
import pytest

from movies.clean.netflix import clean

FIXTURES = Path(__file__).parent / "fixtures"
COUNTRIES = pl.DataFrame({"iso2": ["CZ", "SK", "US"]})


def _raw() -> pl.DataFrame:
    return pl.read_csv(
        FIXTURES / "netflix_weeks.tsv", separator="\t", quote_char=None, infer_schema_length=0
    )


def test_drops_tv_and_weeks_after_snapshot() -> None:
    out = clean(_raw(), COUNTRIES)
    assert out.height == 3
    assert out["week"].max() == date(2026, 9, 27)
    assert "Show C" not in out["title"].to_list()


def test_score_and_sort() -> None:
    out = clean(_raw(), COUNTRIES)
    assert out["week"].to_list() == sorted(out["week"].to_list())
    assert dict(zip(out["title"], out["score"], strict=True)) == {
        'Film "D"': 8,
        "Film A": 10,
        "Film B": 1,
    }


def test_dtypes() -> None:
    out = clean(_raw(), COUNTRIES)
    assert out.schema == {
        "country_iso2": pl.String,
        "week": pl.Date,
        "weekly_rank": pl.Int8,
        "title": pl.String,
        "cumulative_weeks": pl.Int16,
        "score": pl.Int8,
    }


def test_unknown_country_raises() -> None:
    with pytest.raises(ValueError, match="SK"):
        clean(_raw(), pl.DataFrame({"iso2": ["CZ"]}))
