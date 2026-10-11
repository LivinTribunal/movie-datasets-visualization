from datetime import date

import polars as pl
import pytest

from movies.derive.genres import (
    LUMIERE_MIN_FILMS,
    film_genres,
    lumiere_country_genre,
    netflix_country_genre,
)

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
    assert out["estimated_share"].to_list() == [0.0] * out.height


def test_fuzzy_share_counts_only_matched_rows():
    netflix = _chart(
        [
            ("CZ", date(2025, 3, 2), "Exact", 5),
            ("CZ", date(2025, 3, 2), "Fuzzy", 5),
        ]
    )
    titles = pl.DataFrame(
        {"title": ["Exact", "Fuzzy"], "imdb_id": ["tt1", "tt2"], "method": ["exact", "fuzzy"]}
    )
    genres = film_genres(_films([("tt1", ["Drama"]), ("tt2", ["TV Movie"])]), FAMILIES)
    out = netflix_country_genre(netflix, titles, genres)
    assert out["coverage"].to_list() == [0.5]
    assert out["fuzzy_share"].to_list() == [0.0]


def _lumiere(rows):
    return pl.DataFrame(
        rows,
        schema={
            "imdb_id": pl.String,
            "market": pl.String,
            "year": pl.Int16,
            "admissions": pl.Int64,
            "estimated": pl.Boolean,
        },
        orient="row",
    )


def _filler(market, year, n):
    """n extra films so a market-year clears LUMIERE_MIN_FILMS; they have no genres."""
    return [(f"x{market}{i}", market, year, 1, False) for i in range(n)]


def test_lumiere_country_genre_shares_coverage_and_estimated():
    genres = film_genres(_films([("tt1", ["Drama", "Comedy"]), ("tt2", ["Action"])]), FAMILIES)
    rows = [
        ("tt1", "CZ", 2024, 10, False),
        ("tt2", "CZ", 2024, 30, False),
        ("tt1", "GB", 2024, 20, True),
        *_filler("CZ", 2024, LUMIERE_MIN_FILMS - 2),
    ]
    out = lumiere_country_genre(_lumiere(rows), genres, {"CZ", "GB"})

    # GB has 1 film only, so it is dropped
    assert out["country_iso2"].unique().to_list() == ["CZ"]
    assert out["genre"].to_list() == ["Action", "Comedy", "Drama"]
    assert out["score"].to_list() == [30.0, 5.0, 5.0]
    assert out["share"].sum() == pytest.approx(1.0)
    total = 40 + LUMIERE_MIN_FILMS - 2
    assert out["coverage"].to_list() == [pytest.approx(40 / total)] * 3
    assert out["fuzzy_share"].to_list() == [0.0] * 3
    assert out["estimated_share"].to_list() == [0.0] * 3


def test_lumiere_gb_ie_becomes_gb_unless_gb_row_exists():
    genres = film_genres(_films([("tt1", ["Drama"]), ("tt2", ["Action"])]), FAMILIES)
    rows = [
        ("tt1", "GB_IE", 2024, 10, True),  # no GB row for tt1: counts as GB
        ("tt2", "GB_IE", 2024, 99, True),  # tt2 has a GB row: dropped
        ("tt2", "GB", 2024, 30, True),
        *_filler("GB", 2024, LUMIERE_MIN_FILMS),
    ]
    out = lumiere_country_genre(_lumiere(rows), genres, {"GB"})

    assert out["country_iso2"].unique().to_list() == ["GB"]
    assert out["score"].to_list() == [30.0, 10.0]  # Action, Drama
    assert out["estimated_share"].to_list() == [pytest.approx(40 / (40 + LUMIERE_MIN_FILMS))] * 2


def test_lumiere_unknown_market_raises():
    genres = film_genres(_films([("tt1", ["Drama"])]), FAMILIES)
    with pytest.raises(ValueError, match="ZZ"):
        lumiere_country_genre(_lumiere([("tt1", "ZZ", 2024, 1, False)]), genres, {"CZ"})
