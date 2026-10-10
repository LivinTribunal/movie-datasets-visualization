import polars as pl

from movies.export.app import films_table, genre_year, to_columns

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
        "gap": [-5.0, 5.0, None, None],
    },
    schema_overrides={"tmdb_100": pl.Float64},
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
