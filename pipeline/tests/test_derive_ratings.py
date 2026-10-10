import polars as pl

from movies.derive.ratings import ratings


def _films(rows: list[tuple]) -> pl.DataFrame:
    return pl.DataFrame(
        rows,
        schema={
            "imdb_id": pl.String,
            "imdb_rating": pl.Float64,
            "vote_average": pl.Float64,
            "vote_count": pl.Int64,
            "tomatometer": pl.Int8,
            "audience_score": pl.Int8,
        },
        orient="row",
    )


def test_scales_to_100():
    out = ratings(_films([("tt1", 7.5, 6.2, 500, 90, 80)])).row(0, named=True)
    assert out["imdb_100"] == 75.0
    assert out["tmdb_100"] == 62.0
    assert out["tomatometer_100"] == 90.0
    assert out["audience_100"] == 80.0


def test_tmdb_null_under_min_votes():
    out = ratings(_films([("tt1", 7.0, 9.0, 49, None, None), ("tt2", 7.0, 9.0, 50, None, None)]))
    assert out["tmdb_100"].to_list() == [None, 90.0]


def test_gap_is_audience_minus_critics_and_null_when_a_side_is_missing():
    out = ratings(
        _films(
            [
                ("tt1", 7.0, 7.0, 100, 60, 80),
                ("tt2", 7.0, 7.0, 100, None, 80),
                ("tt3", 7.0, 7.0, 100, 60, None),
            ]
        )
    )
    assert out["gap"].to_list() == [20.0, None, None]
