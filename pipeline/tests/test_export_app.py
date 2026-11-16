import datetime as dt

import polars as pl
import pytest

from movies.export.app import (
    country_tables,
    films_table,
    franchises_table,
    to_columns,
    write_country_tables,
    write_films,
    write_franchises,
)
from movies.export.pack import read_pack

GENRES = ["Comedy", "Drama"]
FAMILIES = ["Comedy", "Drama"]
COUNTRIES = ["CZ", "US"]

FILMS = pl.DataFrame(
    {
        "imdb_id": ["tt3", "tt1", "tt2", "tt4"],
        "tmdb_id": [3, 1, 2, None],
        "title": ["C", "A", "B", "D"],
        "genres": [["TV Movie", "Drama"], ["Horror", "TV Movie"], ["Comedy"], ["Drama"]],
        "director": ["Dc", None, "Db", "Dd"],
        "poster_path": ["/c.jpg", "/a.jpg", None, "/d.jpg"],
        "year": pl.Series([2001, 2000, 2000, 2001], dtype=pl.Int16),
        "runtime": [100, 120, None, 90],
        "production_countries": [["US"], ["US", "CZ"], ["CZ"], ["US"]],
        "imdb_votes": [2000, 50000, 3000, 1500],
        "notable": [False, True, False, False],
        "numbers_match": [None, "fuzzy", "exact", None],
    }
)
MONEY = pl.DataFrame(
    {
        "imdb_id": ["tt1", "tt2", "tt3", "tt4"],
        "budget_usd": [900.0, None, None, None],
        "budget_usd2025": [1000.4, None, None, None],
        "revenue_usd": [3500.0, 500.0, None, None],
        "revenue_usd2025": [4000.6, 500.0, None, None],
        "budget_src": ["numbers", None, None, None],
        "revenue_src": ["numbers", "tmdb", None, None],
        "budget_currency": ["EUR", None, None, None],
        "revenue_currency": ["USD", "USD", None, None],
        "budget_disagree": [False, False, False, False],
        "revenue_disagree": [False, True, False, False],
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
        "mc_critic_reviews": [38, None, None, None],
        "mc_user_100": [None, None, None, None],
        "letterboxd_100": [92.0, None, None, None],
        "gap": [-5.0, 5.0, None, None],
    },
    schema_overrides={
        "tmdb_100": pl.Float64,
        "mc_user_100": pl.Float64,
        "mc_critic_reviews": pl.Int32,
    },
)
FILM_GENRES = pl.DataFrame(
    {
        "imdb_id": ["tt1", "tt1", "tt2", "tt3", "tt4"],
        "genre": ["Drama", "Comedy", "Comedy", "Drama", "Drama"],
        "family": ["Drama", "Comedy", "Comedy", "Drama", "Drama"],
        "genre_weight": [0.5, 0.5, 1.0, 1.0, 1.0],
    }
)
FRANCHISES = pl.DataFrame(
    {
        "collection_id": [7, 7, 7],
        "collection_name": ["S", "S", "S"],
        "installment": [2, 1, 3],
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


def _table():
    return films_table(FILMS, MONEY, RATINGS, FILM_GENRES, FRANCHISES)


def test_every_film_sorted_by_votes_and_notable_form_a_prefix():
    out = _table()
    assert out["imdb_id"].to_list() == ["tt1", "tt2", "tt3", "tt4"]
    assert out["imdb_votes"].to_list() == [50000, 3000, 2000, 1500]
    assert out["notable"].to_list() == [True, False, False, False]


def test_flags_lists_and_both_money_kinds_are_kept():
    row = _table().row(0, named=True)
    assert row["money_fuzzy"] is True
    assert row["budget_converted"] is True
    assert row["revenue_converted"] is False
    assert row["budget_usd"] == 900.0
    assert row["budget_usd2025"] == 1000.4
    assert row["genres"] == ["Drama", "Comedy"]
    assert row["families"] == ["Drama", "Comedy"]
    assert row["countries"] == ["US", "CZ"]
    assert row["poster"] == "/a.jpg"


def test_films_table_takes_genres_from_film_genres_not_the_raw_column():
    out = _table()
    assert out["genres"].to_list() == [["Drama", "Comedy"], ["Comedy"], ["Drama"], ["Drama"]]
    assert out["families"].to_list() == [["Drama", "Comedy"], ["Comedy"], ["Drama"], ["Drama"]]


def test_money_fuzzy_needs_numbers_source():
    money = MONEY.with_columns(budget_src=pl.lit("tmdb"), revenue_src=pl.lit("tmdb"))
    out = films_table(FILMS, money, RATINGS, FILM_GENRES, FRANCHISES)
    assert out["money_fuzzy"].to_list() == [False, False, False, False]


def test_film_outside_every_franchise_has_null_collection_id():
    out = _table()
    assert out["collection_id"].to_list() == [7, 7, None, None]
    assert out["installment"].to_list() == [1, 2, None, None]


def test_unknown_production_countries_export_as_empty_list():
    # the app iterates every film's countries; a null list crashed it
    films = FILMS.with_columns(
        production_countries=pl.Series([None, None, ["CZ"], ["US"]], dtype=pl.List(pl.String))
    )
    out = films_table(films, MONEY, RATINGS, FILM_GENRES, FRANCHISES)
    assert out["countries"].to_list() == [[], ["CZ"], [], ["US"]]


def test_to_columns_equal_lengths_and_nulls():
    cols = to_columns(_table())
    assert len({len(v) for v in cols.values()}) == 1
    assert cols["budget_usd2025"] == [1000.4, None, None, None]


def test_write_films_roundtrip_masks_and_flags(tmp_path):
    core, text = tmp_path / "films.pack", tmp_path / "films_text.pack"
    poster = tmp_path / "films_poster.pack"
    write_films(_table(), GENRES, FAMILIES, COUNTRIES, core, text, poster)
    pack = read_pack(core)
    assert pack.rows == 4
    assert pack.meta == {"notable": 1, "genres": GENRES, "families": FAMILIES}
    c = pack.columns
    assert c["imdb"] == [1, 2, 3, 4]
    assert c["tmdb_id"] == [1, 2, 3, None]
    assert c["runtime"] == [120, None, 100, 90]
    assert c["genre_mask"] == [0b11, 0b01, 0b10, 0b10]
    assert c["family_mask"] == [0b11, 0b01, 0b10, 0b10]
    # tt1: budget converted (bit 0) and fuzzy money (bit 4); tt2: revenue sources disagree (bit 3)
    assert c["flags"] == [0b10001, 0b01000, 0, 0]
    assert c["countries"] == [["US", "CZ"], ["CZ"], ["US"], ["US"]]
    assert c["budget_src"] == ["numbers", None, None, None]
    assert c["budget_usd2025"][0] == pytest.approx(1000.4, rel=1e-6)
    assert c["budget_usd2025"][1] is None
    assert c["imdb_100"] == [70.0, 60.0, None, None]
    assert c["gap"] == [-5.0, 5.0, None, None]
    assert c["mc_critic_reviews"] == [38, None, None, None]
    assert c["collection_id"] == [7, 7, None, None]
    assert c["installment"] == [1, 2, None, None]
    text_cols = read_pack(text).columns
    assert text_cols["title"] == ["A", "B", "C", "D"]
    assert text_cols["director"] == [None, "Db", "Dc", "Dd"]
    assert "poster" not in text_cols
    assert read_pack(poster).columns["poster"] == ["/a.jpg", None, "/c.jpg", "/d.jpg"]


def _shares(country, year, genre, entries=30):
    return pl.DataFrame(
        {
            "country_iso2": [country],
            "year": pl.Series([year], dtype=pl.Int32),
            "genre": [genre],
            "family": [genre],
            "score": [2.5],
            "share": [1.0],
            "coverage": [0.5],
            "fuzzy_share": [0.0],
            "estimated_share": [0.0],
            "entries": [entries],
        }
    )


def test_country_tables_one_year_row_per_source_country_year():
    sources = [
        (
            "netflix",
            "chart_score",
            pl.concat([_shares("CZ", 2025, "Drama"), _shares("CZ", 2025, "Comedy")]),
        ),
        ("cinema", "admissions", _shares("CZ", 2024, "Drama")),
        ("cinema", "gross_usd", _shares("US", 2024, "Comedy")),
    ]
    genre, year = country_tables(sources, GENRES)
    assert genre.select("source", "country", "year", "genre").rows() == [
        ("cinema", "CZ", 2024, 1),
        ("cinema", "US", 2024, 0),
        ("netflix", "CZ", 2025, 0),
        ("netflix", "CZ", 2025, 1),
    ]
    assert year.select("source", "country", "year", "measure").rows() == [
        ("cinema", "CZ", 2024, "admissions"),
        ("cinema", "US", 2024, "gross_usd"),
        ("netflix", "CZ", 2025, "chart_score"),
    ]
    assert year["entries"].to_list() == [30, 30, 30]


def test_country_tables_concat_mixed_dtypes():
    a = _shares("CZ", 2025, "Drama").with_columns(entries=pl.Series([30], dtype=pl.UInt32))
    b = _shares("US", 2024, "Comedy").with_columns(
        year=pl.Series([2024], dtype=pl.Int16),
        entries=pl.Series([40], dtype=pl.Int64),
        score=pl.Series([3], dtype=pl.Int64),
    )
    genre, year = country_tables(
        [("netflix", "chart_score", a), ("cinema", "gross_usd", b)], GENRES
    )
    assert genre["year"].to_list() == [2024, 2025]
    assert year["entries"].to_list() == [40, 30]


def test_write_country_tables_roundtrip(tmp_path):
    genre, year = country_tables([("cinema", "gross_usd", _shares("US", 2024, "Comedy"))], GENRES)
    gpath, ypath = tmp_path / "g.pack", tmp_path / "y.pack"
    write_country_tables(genre, year, GENRES, COUNTRIES, gpath, ypath)
    g, y = read_pack(gpath).columns, read_pack(ypath).columns
    assert (g["source"], g["country"], g["year"], g["genre"], g["score"]) == (
        ["cinema"],
        ["US"],
        [2024],
        [0],
        [2.5],
    )
    assert (y["entries"], y["measure"], y["coverage"]) == ([30], ["gross_usd"], [0.5])


def test_franchises_table_film_row_year_and_family_mask():
    films_out = _table()
    out = franchises_table(FRANCHISES, films_out, FILM_GENRES, FAMILIES)
    assert out["installment"].to_list() == [1, 2, 3]
    assert out["film_row"].to_list() == [0, 1, None]
    assert out["year"].to_list() == [2001, 2003, 1999]
    # the first part, tt1, is Drama and Comedy
    assert out["family_mask"].to_list() == [0b11, 0b11, 0b11]
    assert "imdb_100_vs_prev" not in out.columns
    no_genres = franchises_table(FRANCHISES, films_out, FILM_GENRES.head(0), FAMILIES)
    assert no_genres["family_mask"].to_list() == [0, 0, 0]


def test_write_franchises_roundtrip(tmp_path):
    out = franchises_table(FRANCHISES, _table(), FILM_GENRES, FAMILIES)
    path = tmp_path / "f.pack"
    write_franchises(out, path)
    pack = read_pack(path)
    assert pack.meta == {"collections": [[7, "S"]]}
    assert pack.columns["film_row"] == [0, 1, None]
    assert pack.columns["imdb_100"] == [80.0, 70.0, None]
    assert pack.columns["imdb_100_vs_first"] == [0.0, -10.0, None]
    assert pack.columns["title"] == ["One", "Two", "Nine"]
