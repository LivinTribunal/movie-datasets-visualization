import datetime as dt

import polars as pl

from movies.export.app import films_table, franchises_table, genre_year, to_columns
from movies.validate.app import SCHEMA

FILMS = pl.DataFrame(
    {
        "imdb_id": ["tt3", "tt1", "tt2", "tt4"],
        "tmdb_id": [3, 1, 2, 4],
        "title": ["C", "A", "B", "D"],
        "year": pl.Series([2001, 2000, 2000, 2001], dtype=pl.Int16),
        "genres": [["Drama"], ["Drama", "Comedy"], ["Comedy"], ["Drama"]],
        "production_countries": [["US"], ["US", "CZ"], ["CZ"], ["US"]],
        "imdb_votes": [2000, 50000, 3000, 1500],
        "notable": [False, True, False, False],
        "numbers_match": [None, "fuzzy", "exact", None],
    }
)
MONEY = pl.DataFrame(
    {
        "imdb_id": ["tt1", "tt2", "tt3", "tt4"],
        "budget_usd2025": [1000.4, None, None, None],
        "revenue_usd2025": [4000.6, 500.0, None, None],
        "budget_src": ["numbers", None, None, None],
        "revenue_src": ["numbers", "tmdb", None, None],
        "budget_currency": ["EUR", None, None, None],
        "revenue_currency": ["USD", "USD", None, None],
        "budget_disagree": [False, False, False, False],
        "revenue_disagree": [False, False, False, False],
        "roi": [3.00049, None, None, None],
    }
)
RATINGS = pl.DataFrame(
    {
        "imdb_id": ["tt1", "tt2", "tt3", "tt4"],
        "imdb_100": [70.04, 60.0, None, None],
        "tmdb_100": [None, None, None, None],
        "tomatometer_100": [80.0, 50.0, 90.0, None],
        "audience_100": [75.0, 55.0, None, None],
        "metascore_100": [82.04, None, None, None],
        "mc_user_100": [None, None, None, None],
        "letterboxd_100": [92.0, None, None, None],
        "gap": [-5.0, 5.0, None, None],
    },
    schema_overrides={"tmdb_100": pl.Float64, "mc_user_100": pl.Float64},
)
FILM_GENRES = pl.DataFrame(
    {
        "imdb_id": ["tt1", "tt1", "tt2", "tt3", "tt4"],
        "genre": ["Drama", "Comedy", "Comedy", "Drama", "Drama"],
        "family": ["Drama", "Comedy", "Comedy", "Drama", "Drama"],
        "genre_weight": [0.5, 0.5, 1.0, 1.0, 1.0],
    }
)


def test_row_selection_notable_or_both_rt_scores():
    out = films_table(FILMS, MONEY, RATINGS, FILM_GENRES)
    # tt3 has only a tomatometer and is not notable; tt4 has nothing
    assert out["imdb_id"].to_list() == ["tt1", "tt2"]


def test_flags_rounding_and_lists():
    row = films_table(FILMS, MONEY, RATINGS, FILM_GENRES).row(0, named=True)
    assert row["money_fuzzy"] is True
    assert row["budget_converted"] is True
    assert row["revenue_converted"] is False
    assert row["budget_usd2025"] == 1000
    assert row["roi"] == 3.0
    assert row["imdb_100"] == 70.0
    assert row["genres"] == ["Drama", "Comedy"]
    assert row["families"] == ["Drama", "Comedy"]
    assert row["countries"] == ["US", "CZ"]


def test_money_fuzzy_needs_numbers_source():
    money = MONEY.with_columns(budget_src=pl.lit("tmdb"), revenue_src=pl.lit("tmdb"))
    out = films_table(FILMS, money, RATINGS, FILM_GENRES)
    assert out["money_fuzzy"].to_list() == [False, False]
    assert films_table(FILMS, MONEY, RATINGS, FILM_GENRES)["budget_converted"][1] is False


def test_genre_year_weights_and_notable_subset():
    out = genre_year(FILMS, MONEY, FILM_GENRES)
    for subset, total in (("working", 4.0), ("notable", 1.0)):
        assert abs(out.filter(pl.col("subset") == subset)["films"].sum() - total) < 1e-9
    row = out.filter(
        (pl.col("subset") == "working") & (pl.col("year") == 2000) & (pl.col("genre") == "Comedy")
    ).row(0, named=True)
    assert row["films"] == 1.5
    assert row["votes"] == 0.5 * 50000 + 3000
    assert row["revenue_usd2025"] == round(0.5 * 4000.6 + 500)
    assert row["revenue_films"] == 2
    no_rev = out.filter((pl.col("year") == 2001) & (pl.col("subset") == "working"))
    assert no_rev["revenue_usd2025"].to_list() == [None]
    assert out.select("subset", "year", "genre").rows() == sorted(
        out.select("subset", "year", "genre").rows()
    )


def test_to_columns_equal_lengths_and_nulls():
    cols = to_columns(films_table(FILMS, MONEY, RATINGS, FILM_GENRES))
    assert len({len(v) for v in cols.values()}) == 1
    assert cols["budget_usd2025"] == [1000, None]
    assert cols["tmdb_100"] == [None, None]


def test_unknown_production_countries_export_as_empty_list():
    # the app iterates every film's countries; a null list crashed it
    films = FILMS.with_columns(
        production_countries=pl.Series([None, None, ["CZ"], ["US"]], dtype=pl.List(pl.String))
    )
    out = films_table(films, MONEY, RATINGS, FILM_GENRES)
    assert out["countries"].to_list() == [[], ["CZ"]]


FRANCHISES = pl.DataFrame(
    {
        "collection_id": [7, 7, 3],
        "collection_name": ["S", "S", "T"],
        "installment": [2, 1, 1],
        "n_released": [3, 3, 3],
        "tmdb_id": [2, 1, 9],
        "imdb_id": ["tt2", "tt1", None],
        "title": ["Two", "One", "Nine"],
        "release_date": [dt.date(2003, 1, 1), dt.date(2001, 5, 1), dt.date(1999, 1, 1)],
        "imdb_100": [70.04, 80.0, None],
        "imdb_100_vs_prev": [-9.96, None, None],
        "imdb_100_vs_first": [-9.96, 0.0, None],
        "tomatometer_100": [None, 90.0, None],
        "audience_100": pl.Series([None, None, None], dtype=pl.Float64),
        "revenue_usd2025": [50.4, 100.0, None],
        "revenue_vs_prev": [0.50049, None, None],
        "revenue_vs_first": [0.50049, 1.0, None],
    }
)


def test_films_table_includes_scraped_scores_in_schema_order():
    out = films_table(FILMS, MONEY, RATINGS, FILM_GENRES)
    assert out.columns == SCHEMA["films.json"]
    assert out["metascore_100"].to_list()[0] == 82.0
    assert out["letterboxd_100"].to_list()[0] == 92.0


def test_franchises_table_year_rounding_and_order():
    out = franchises_table(FRANCHISES)
    assert out["collection_id"].to_list() == [3, 7, 7]
    assert out["installment"].to_list() == [1, 1, 2]
    assert out["year"].to_list() == [1999, 2001, 2003]
    assert out["imdb_100"].to_list() == [None, 80.0, 70.0]
    assert out["revenue_usd2025"].to_list() == [None, 100, 50]
    assert out["revenue_vs_prev"].to_list() == [None, None, 0.5]
