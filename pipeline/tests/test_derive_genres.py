from datetime import date

import polars as pl
import pytest

from movies.derive.genres import film_genres, netflix_country_genre

FAMILIES = pl.DataFrame(
    {
        "genre": ["Drama", "Comedy", "Action"],
        "family": ["Drama", "Comedy", "Action"],
    }
)


def _films(rows: list[tuple]) -> pl.DataFrame:
    return pl.DataFrame(
        rows, schema={"imdb_id": pl.String, "genres": pl.List(pl.String)}, orient="row"
    )


def test_weights_sum_to_one_per_film():
    out = film_genres(_films([("tt1", ["Drama", "Comedy"]), ("tt2", ["Action"])]), FAMILIES)
    assert out["genre_weight"].to_list() == [0.5, 0.5, 1.0]


def test_tv_movie_dropped_and_weight_recomputed():
    out = film_genres(_films([("tt1", ["Drama", "TV Movie"]), ("tt2", ["TV Movie"])]), FAMILIES)
    assert out.rows() == [("tt1", "Drama", "Drama", 1.0)]


def test_unknown_genre_raises():
    with pytest.raises(ValueError, match="Western"):
        film_genres(_films([("tt1", ["Drama", "Western"])]), FAMILIES)


def _chart(rows: list[tuple]) -> pl.DataFrame:
    return pl.DataFrame(
        rows,
        schema={"country_iso2": pl.String, "week": pl.Date, "title": pl.String, "score": pl.Int8},
        orient="row",
    )


def test_netflix_country_genre_shares_coverage_and_fuzzy():
    netflix = _chart(
        [
            ("CZ", date(2025, 3, 2), "Both", 10),
            ("CZ", date(2025, 3, 2), "Ghost", 10),
            ("CZ", date(2025, 3, 2), "Fuzzy", 5),
            ("SK", date(2024, 12, 29), "Both", 4),
        ]
    )
    titles = pl.DataFrame(
        {
            "title": ["Both", "Ghost", "Fuzzy"],
            "imdb_id": ["tt1", None, "tt2"],
            "method": ["exact", None, "fuzzy"],
        }
    )
    genres = film_genres(_films([("tt1", ["Drama", "Comedy"]), ("tt2", ["Action"])]), FAMILIES)
    out = netflix_country_genre(netflix, titles, genres)

    cz = out.filter(pl.col("country_iso2") == "CZ")
    assert cz["genre"].to_list() == ["Action", "Comedy", "Drama"]
    assert cz["score"].to_list() == [5.0, 5.0, 5.0]
    assert cz["share"].sum() == pytest.approx(1.0)
    assert cz["coverage"].to_list() == [pytest.approx(15 / 25)] * 3
    assert cz["fuzzy_share"].to_list() == [pytest.approx(5 / 25)] * 3

    sk = out.filter(pl.col("country_iso2") == "SK")
    assert sk["year"].to_list() == [2024, 2024]
    assert sk["share"].to_list() == [0.5, 0.5]
    assert sk["coverage"].to_list() == [1.0, 1.0]
    assert sk["fuzzy_share"].to_list() == [0.0, 0.0]
