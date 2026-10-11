import polars as pl
import pytest

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


def _mc(rows: list[tuple]) -> pl.DataFrame:
    return pl.DataFrame(
        rows,
        schema={
            "imdb_id": pl.String,
            "metascore": pl.Int8,
            "mc_critic_reviews": pl.Int32,
            "mc_user_score": pl.Float64,
            "mc_user_ratings": pl.Int32,
        },
        orient="row",
    )


def test_metacritic_and_letterboxd_scale_to_100():
    lb = pl.DataFrame({"imdb_id": ["tt1"], "letterboxd_avg": [4.6]})
    out = ratings(_films([("tt1", 7.5, 6.2, 500, 90, 80)]), _mc([("tt1", 82, 38, 9.3, 40)]), lb)
    row = out.row(0, named=True)
    assert row["metascore_100"] == 82.0
    assert row["mc_critic_reviews"] == 38
    assert row["mc_user_100"] == pytest.approx(93.0)
    assert row["letterboxd_100"] == pytest.approx(92.0)


def test_mc_user_null_under_min_user_ratings():
    mc = _mc([("tt1", 50, 5, 9.0, 9), ("tt2", 50, 5, 9.0, 10)])
    out = ratings(_films([("tt1", 7.0, 7.0, 100, 60, 80), ("tt2", 7.0, 7.0, 100, 60, 80)]), mc)
    assert out["mc_user_100"].to_list() == [None, pytest.approx(90.0)]


def test_missing_frames_give_null_columns_in_order():
    out = ratings(_films([("tt1", 7.5, 6.2, 500, 90, 80)]))
    assert out.columns == [
        "imdb_id", "imdb_100", "tmdb_100", "tomatometer_100", "metascore_100",
        "mc_critic_reviews", "audience_100", "mc_user_100", "letterboxd_100", "gap",
    ]  # fmt: skip
    assert out.select("metascore_100", "mc_critic_reviews", "mc_user_100").row(0) == (None,) * 3
