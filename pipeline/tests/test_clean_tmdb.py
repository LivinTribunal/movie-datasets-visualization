from datetime import date
from pathlib import Path

import polars as pl
import pytest

from movies.clean.tmdb import clean

FIXTURES = Path(__file__).parent / "fixtures"

NAMES = pl.DataFrame(
    {
        "name": ["United States of America", "United Kingdom", "Russia", "Soviet Union"],
        "iso2": ["US", "GB", "RU", "RU"],
    }
)


@pytest.fixture(scope="module")
def films() -> pl.DataFrame:
    raw = pl.scan_csv(FIXTURES / "tmdb_sample.csv", infer_schema=False)
    return clean(raw, NAMES)


def _row(films: pl.DataFrame, tmdb_id: int) -> dict:
    return films.filter(pl.col("tmdb_id") == tmdb_id).row(0, named=True)


def test_typed_row(films: pl.DataFrame) -> None:
    r = _row(films, 1)
    assert (r["budget"], r["revenue"], r["runtime"], r["year"]) == (5000000.0, 1000000.0, 120, 1999)
    assert r["release_date"] == date(1999, 5, 4)
    assert (r["vote_count"], r["imdb_votes"]) == (100, 500)
    assert r["status"] == "Released" and r["certification_us"] == "PG"
    assert films["tmdb_id"].to_list() == sorted(films["tmdb_id"].to_list())


def test_zero_sentinels_become_null(films: pl.DataFrame) -> None:
    r = _row(films, 2)
    assert r["budget"] is None and r["revenue"] is None and r["runtime"] is None
    assert r["budget_under_1000"] is False


def test_small_budget_dropped_and_flagged(films: pl.DataFrame) -> None:
    r = _row(films, 3)
    assert r["budget"] is None and r["budget_under_1000"] is True


def test_vote_average_null_without_votes(films: pl.DataFrame) -> None:
    assert _row(films, 2)["vote_average"] is None
    assert _row(films, 3)["vote_average"] == 6.0


def test_future_and_malformed_dates_null(films: pl.DataFrame) -> None:
    for tmdb_id in (4, 5):
        r = _row(films, tmdb_id)
        assert r["release_date"] is None and r["year"] is None


def test_malformed_imdb_id_null(films: pl.DataFrame) -> None:
    assert _row(films, 6)["imdb_id"] is None
    assert _row(films, 1)["imdb_id"] == "tt0000001"


def test_duplicate_keeps_more_imdb_votes(films: pl.DataFrame) -> None:
    assert films.filter(pl.col("imdb_id") == "tt0000007")["tmdb_id"].to_list() == [8]


def test_genres_list(films: pl.DataFrame) -> None:
    assert _row(films, 1)["genres"] == ["Drama", "Romance", "Crime"]
    assert _row(films, 9)["genres"] == ["Drama"]
    assert _row(films, 2)["genres"] is None


def test_production_countries(films: pl.DataFrame) -> None:
    assert _row(films, 1)["production_countries"] == ["US", "GB"]
    assert _row(films, 9)["production_countries"] == ["RU"]
    assert _row(films, 2)["production_countries"] is None
