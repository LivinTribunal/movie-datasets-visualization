import datetime as dt

import polars as pl

from movies.derive.franchises import franchises

D = dt.date


def _parts(rows: list[tuple]) -> pl.DataFrame:
    return pl.DataFrame(
        rows,
        schema={
            "collection_id": pl.Int64,
            "collection_name": pl.String,
            "tmdb_id": pl.Int64,
            "title": pl.String,
            "release_date": pl.Date,
        },
        orient="row",
    )


FILMS = pl.DataFrame({"imdb_id": ["tt1", "tt2", "tt3"], "tmdb_id": [1, 2, 3]})
RATINGS = pl.DataFrame(
    {
        "imdb_id": ["tt1", "tt2", "tt3"],
        "imdb_100": [80.0, 70.0, 75.0],
        "tomatometer_100": [90.0, None, None],
        "audience_100": [None, None, None],
    }
)
MONEY = pl.DataFrame({"imdb_id": ["tt1", "tt2", "tt3"], "revenue_usd2025": [100.0, 50.0, None]})
PARTS = _parts(
    [
        (7, "S", 3, "Three", D(2005, 1, 1)),
        (7, "S", 1, "One", D(2001, 1, 1)),
        (7, "S", 2, "Two", D(2003, 1, 1)),
        (7, "S", 4, "Four", D(2030, 1, 1)),
        (7, "S", 5, "Five", None),
        (8, "Pair", 6, "A", D(2001, 1, 1)),
        (8, "Pair", 7, "B", D(2002, 1, 1)),
    ]
)


def test_numbering_by_date_drops_unreleased_and_small_collections():
    out = franchises(PARTS, FILMS, RATINGS, MONEY)
    assert out["collection_id"].unique().to_list() == [7]
    assert out["tmdb_id"].to_list() == [1, 2, 3]
    assert out["installment"].to_list() == [1, 2, 3]
    assert out["n_released"].to_list() == [3, 3, 3]


def test_changes_vs_prev_and_first():
    out = franchises(PARTS, FILMS, RATINGS, MONEY)
    assert out["imdb_100_vs_prev"].to_list() == [None, -10.0, 5.0]
    assert out["imdb_100_vs_first"].to_list() == [0.0, -10.0, -5.0]
    assert out["revenue_vs_prev"].to_list() == [None, 0.5, None]
    assert out["revenue_vs_first"].to_list() == [1.0, 0.5, None]


def test_part_outside_films_keeps_installment_with_null_ratings():
    out = franchises(PARTS, FILMS.filter(pl.col("tmdb_id") != 2), RATINGS, MONEY)
    mid = out.filter(pl.col("installment") == 2).row(0, named=True)
    assert mid["tmdb_id"] == 2 and mid["imdb_id"] is None and mid["imdb_100"] is None
    assert mid["imdb_100_vs_prev"] is None and mid["revenue_vs_first"] is None
