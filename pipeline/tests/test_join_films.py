from datetime import date

import polars as pl

from movies.join.films import attach_numbers, attach_rt, match_netflix, working_subset

NO_OVERRIDES = pl.DataFrame(schema={"key": pl.String, "imdb_id": pl.String})


def _tmdb(rows: list[tuple]) -> pl.DataFrame:
    return pl.DataFrame(
        rows,
        schema={
            "imdb_id": pl.String,
            "title": pl.String,
            "original_title": pl.String,
            "status": pl.String,
            "year": pl.Int16,
            "imdb_votes": pl.Int64,
        },
        orient="row",
    )


def test_working_subset_filters_and_flags_notable():
    tmdb = _tmdb(
        [
            ("tt1", "A", "A", "Released", 2000, 20_000),
            ("tt2", "B", "B", "Released", 2000, 999),
            ("tt3", "C", "C", "Planned", 2000, 5000),
            ("tt4", "D", "D", "Released", 1899, 5000),
            ("tt5", "E", "E", "Released", 2010, 1000),
            (None, "F", "F", "Released", 2010, 5000),
        ]
    )
    out = working_subset(tmdb).sort("imdb_id")
    assert out["imdb_id"].to_list() == ["tt1", "tt5"]
    assert out["notable"].to_list() == [True, False]


def test_attach_rt_prefers_row_with_tomatometer():
    films = _tmdb([("tt1", "A", "A", "Released", 2000, 5000)])
    ids = pl.DataFrame({"imdb_id": ["tt1"], "rt_id": ["m/a|m/b"], "qid": ["Q1"]})
    rt = pl.DataFrame(
        {
            "rt_id": ["m/a", "m/b"],
            "tomatometer": [None, 80],
            "audience_score": [70, 75],
            "box_office_usd": [None, None],
            "release_date_theaters": [None, None],
        },
        schema_overrides={
            "tomatometer": pl.Int8,
            "audience_score": pl.Int8,
            "release_date_theaters": pl.Date,
        },
    )
    out = attach_rt(films, ids, rt)
    assert out["rt_slug"].to_list() == ["m/b"]
    assert out["tomatometer"].to_list() == [80]


def _numbers(metrics_title: str | None, budgets_title: str):
    schema = {
        "numbers_id": pl.Int64,
        "title": pl.String,
        "year": pl.Int64,
        "budget": pl.Float64,
        "domestic_gross": pl.Float64,
        "worldwide_gross": pl.Float64,
        "international_box_office": pl.Float64,
        "opening_weekend": pl.Float64,
        "franchise": pl.String,
    }
    rows = [(1, metrics_title, 2000, 10.0, 1.0, 5.0, 4.0, 0.5, "F")] if metrics_title else []
    metrics = pl.DataFrame(rows, schema=schema, orient="row")
    budgets = pl.DataFrame(
        {
            "numbers_rank": [7],
            "title": [budgets_title],
            "year": [2000],
            "budget": [99.0],
            "domestic_gross": [2.0],
            "worldwide_gross": [50.0],
        }
    )
    return metrics, budgets


def test_numbers_metrics_beats_budgets():
    films = _tmdb([("tt1", "Alpha", "Alpha", "Released", 2000, 5000)])
    metrics, budgets = _numbers("Alpha", "Alpha")
    out, _ = attach_numbers(films, metrics, budgets, NO_OVERRIDES)
    row = out.row(0, named=True)
    assert row["numbers_key"] == "metrics:1"
    assert row["numbers_budget"] == 10.0
    assert row["numbers_match"] == "exact"


def test_override_replaces_fuzzy_match():
    films = _tmdb(
        [
            ("tt1", "Alpha Beta Gamma", "Alpha Beta Gamma", "Released", 2000, 5000),
            ("tt2", "Something Else", "Something Else", "Released", 2000, 5000),
        ]
    )
    metrics, budgets = _numbers(None, "Alpha Beta Gamm")
    fuzzy, _ = attach_numbers(films, metrics, budgets, NO_OVERRIDES)
    assert fuzzy.filter(pl.col("numbers_match") == "fuzzy")["imdb_id"].to_list() == ["tt1"]
    ov = pl.DataFrame({"key": ["budgets:7"], "imdb_id": ["tt2"]})
    out, _ = attach_numbers(films, metrics, budgets, ov)
    hit = out.filter(pl.col("numbers_key").is_not_null())
    assert hit["imdb_id"].to_list() == ["tt2"]
    assert hit["numbers_match"].to_list() == ["override"]


def _netflix() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "title": ["Old Film", "Ghost"],
            "week": [date(2020, 1, 6), date(2020, 1, 6)],
            "score": [1, 2],
        }
    )


def test_netflix_film_released_after_first_week_stays_unmatched():
    tmdb = _tmdb(
        [
            ("tt1", "Old Film", "Old Film", "Released", 2021, 5000),
            ("tt2", "Other", "Other", "Released", 2019, 5000),
        ]
    )
    out = match_netflix(_netflix(), tmdb, NO_OVERRIDES)
    assert out.filter(pl.col("title") == "Old Film")["imdb_id"].to_list() == [None]


def test_netflix_unmatched_title_is_kept():
    tmdb = _tmdb([("tt1", "Old Film", "Old Film", "Released", 2019, 5000)])
    out = match_netflix(_netflix(), tmdb, NO_OVERRIDES).sort("title")
    assert out["title"].to_list() == ["Ghost", "Old Film"]
    assert out["imdb_id"].to_list() == [None, "tt1"]
    assert out["method"].to_list() == [None, "exact"]


def test_rt_id_shared_by_two_films_goes_to_the_closest_year():
    films = _tmdb(
        [
            ("tt1", "Hit", "Hit", "Released", 2020, 1000),
            ("tt2", "Hit", "Hit", "Released", 2022, 9000),
        ]
    )
    ids = pl.DataFrame({"imdb_id": ["tt1", "tt2"], "rt_id": ["m/hit", "m/hit"]})
    rt = pl.DataFrame(
        {
            "rt_id": ["m/hit"],
            "tomatometer": [50],
            "audience_score": [60],
            "box_office_usd": [None],
            "release_date_theaters": [date(2020, 7, 10)],
        },
        schema_overrides={"tomatometer": pl.Int8, "audience_score": pl.Int8},
    )
    out = attach_rt(films, ids, rt).sort("imdb_id")
    assert out["rt_slug"].to_list() == ["m/hit", None]


def test_numbers_override_beats_fuzzy_metrics_and_values_fill_from_twin():
    films = _tmdb([("tt1", "Alpha Beta Gamma", "Alpha Beta Gamma", "Released", 2000, 5000)])
    metrics, budgets = _numbers("Alpha Beta Gamm", "Zzz")
    ov = pl.DataFrame({"key": ["budgets:7"], "imdb_id": ["tt1"]})
    row = attach_numbers(films, metrics, budgets, ov)[0].row(0, named=True)
    assert (row["numbers_key"], row["numbers_match"]) == ("budgets:7", "override")

    metrics, budgets = _numbers("Alpha Beta Gamma", "Alpha Beta Gamma")
    metrics = metrics.with_columns(worldwide_gross=pl.lit(None, dtype=pl.Float64))
    row = attach_numbers(films, metrics, budgets, NO_OVERRIDES)[0].row(0, named=True)
    assert row["numbers_key"] == "metrics:1"
    assert (row["numbers_budget"], row["numbers_worldwide_gross"]) == (10.0, 50.0)


def test_numbers_metrics_year_a_century_late_takes_the_budgets_year():
    # the metrics file stores 1925 films as 2025; the budgets file has the 4-digit year
    films = _tmdb([("tt1", "Ben-Hur", "Ben-Hur", "Released", 1925, 5000)])
    metrics, budgets = _numbers("Ben-Hur", "Ben-Hur")
    metrics = metrics.with_columns(year=pl.lit(2025, dtype=pl.Int64))
    budgets = budgets.with_columns(year=pl.lit(1925, dtype=pl.Int64))
    row = attach_numbers(films, metrics, budgets, NO_OVERRIDES)[0].row(0, named=True)
    assert row["numbers_key"] == "metrics:1"
