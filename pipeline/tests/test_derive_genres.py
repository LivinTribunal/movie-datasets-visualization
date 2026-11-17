from datetime import date

import polars as pl
import pytest

from movies.derive.genres import (
    LUMIERE_MIN_FILMS,
    film_genres,
    imdb_genre_year,
    kobis_as_lumiere,
    lumiere_country_genre,
    netflix_country_genre,
    production_country_genre,
    us_cinema_country_genre,
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


def test_netflix_entries_count_distinct_matched_films():
    netflix = _chart(
        [
            ("CZ", date(2025, 3, 2), "Both", 10),
            ("CZ", date(2025, 3, 9), "Both", 8),
            ("CZ", date(2025, 3, 9), "Ghost", 5),
            ("CZ", date(2025, 3, 9), "Other", 5),
        ]
    )
    titles = pl.DataFrame(
        {
            "title": ["Both", "Ghost", "Other"],
            "imdb_id": ["tt1", None, "tt2"],
            "method": ["exact", None, "exact"],
        }
    )
    genres = film_genres(_films([("tt1", ["Drama", "Comedy"]), ("tt2", ["Action"])]), FAMILIES)
    out = netflix_country_genre(netflix, titles, genres)
    assert out.columns[-1] == "entries"
    assert out["entries"].to_list() == [2] * out.height


def test_lumiere_entries_count_films_with_genres():
    genres = film_genres(_films([("tt1", ["Drama", "Comedy"]), ("tt2", ["Action"])]), FAMILIES)
    rows = [
        ("tt1", "CZ", 2024, 10, False),
        ("tt2", "CZ", 2024, 30, False),
        *_filler("CZ", 2024, LUMIERE_MIN_FILMS),  # no genres, but they count towards the minimum
    ]
    out = lumiere_country_genre(_lumiere(rows), genres, {"CZ"})
    assert out.columns[-1] == "entries"
    assert out["entries"].to_list() == [2] * out.height


def _wide_films(rows: list[tuple]) -> pl.DataFrame:
    return pl.DataFrame(
        rows,
        schema={
            "imdb_id": pl.String,
            "year": pl.Int16,
            "production_countries": pl.List(pl.String),
            "numbers_domestic_gross": pl.Float64,
            "numbers_match": pl.String,
        },
        orient="row",
    )


def test_production_counts_a_coproduction_in_each_country():
    genres = film_genres(_films([("tt1", ["Drama", "Comedy"])]), FAMILIES)
    films = _wide_films([("tt1", 2000, ["US", "GB"], None, None)])
    out = production_country_genre(films, genres)
    assert out["country_iso2"].to_list() == ["GB", "GB", "US", "US"]
    assert out["genre"].to_list() == ["Comedy", "Drama"] * 2
    assert out["score"].to_list() == [0.5] * 4
    assert out.group_by("country_iso2").agg(pl.col("share").sum())["share"].to_list() == [1.0, 1.0]
    assert out["entries"].to_list() == [1] * 4
    assert out["coverage"].to_list() == [1.0] * 4
    assert out.columns[-1] == "entries"


def test_production_drops_null_year_and_null_country():
    genres = film_genres(
        _films([("tt1", ["Drama"]), ("tt2", ["Drama"]), ("tt3", ["Drama"])]), FAMILIES
    )
    films = _wide_films(
        [
            ("tt1", None, ["US"], None, None),
            ("tt2", 2000, None, None, None),
            ("tt3", 2000, ["US"], None, None),
        ]
    )
    out = production_country_genre(films, genres)
    assert out.select("country_iso2", "year", "entries").rows() == [("US", 2000, 1)]


def test_us_cinema_shares_are_gross_weighted():
    genres = film_genres(_films([("tt1", ["Drama", "Comedy"]), ("tt2", ["Action"])]), FAMILIES)
    films = _wide_films(
        [("tt1", 2000, ["US"], 100.0, "exact"), ("tt2", 2000, ["US"], 300.0, "exact")]
    )
    out = us_cinema_country_genre(films, genres, min_films=1)
    assert out["country_iso2"].unique().to_list() == ["US"]
    assert out["year"].dtype == pl.Int16
    assert out["genre"].to_list() == ["Action", "Comedy", "Drama"]
    assert out["score"].to_list() == [300.0, 50.0, 50.0]
    assert out["share"].to_list() == [0.75, 0.125, 0.125]
    assert out["entries"].to_list() == [2] * 3
    assert out.columns[-1] == "entries"


def test_us_cinema_drops_years_under_min_films():
    genres = film_genres(
        _films([("tt1", ["Drama"]), ("tt2", ["Drama"]), ("tt3", ["Drama"])]), FAMILIES
    )
    films = _wide_films(
        [
            ("tt1", 2000, ["US"], 10.0, "exact"),
            ("tt2", 2000, ["US"], 10.0, "exact"),
            ("tt3", 2001, ["US"], 10.0, "exact"),
        ]
    )
    out = us_cinema_country_genre(films, genres, min_films=2)
    assert out["year"].to_list() == [2000]


def test_us_cinema_fuzzy_share_and_coverage():
    genres = film_genres(_films([("tt1", ["Drama"]), ("tt2", ["Action"])]), FAMILIES)
    films = _wide_films(
        [
            ("tt1", 2000, ["US"], 60.0, "exact"),
            ("tt2", 2000, ["US"], 20.0, "fuzzy"),
            ("tt3", 2000, ["US"], 20.0, "exact"),  # no genres
            ("tt4", 2000, ["US"], None, None),  # no gross: ignored
        ]
    )
    out = us_cinema_country_genre(films, genres, min_films=1)
    assert out["coverage"].to_list() == [pytest.approx(0.8)] * 2
    assert out["fuzzy_share"].to_list() == [pytest.approx(0.2)] * 2
    assert out["estimated_share"].to_list() == [0.0] * 2
    assert out["entries"].to_list() == [2] * 2


MAPPING = pl.DataFrame(
    {
        "imdb_genre": ["Drama", "Crime", "Film-Noir", "Sport", "Short", "News"],
        "genre": ["Drama", "Crime", "Crime", None, None, None],
    },
    schema={"imdb_genre": pl.String, "genre": pl.String},
)
IMDB_FAMILIES = pl.DataFrame({"genre": ["Drama", "Crime"], "family": ["Drama", "Crime"]})


def _titles(rows: list[tuple]) -> pl.DataFrame:
    return pl.DataFrame(
        rows,
        schema={
            "imdb_id": pl.String,
            "title_type": pl.String,
            "year": pl.Int16,
            "genres": pl.List(pl.String),
        },
        orient="row",
    )


def test_imdb_shorts_count_only_before_1920():
    titles = _titles(
        [
            ("tt1", "short", 1915, ["Drama"]),
            ("tt2", "short", 1925, ["Drama"]),
            ("tt3", "movie", 1915, ["Drama"]),
        ]
    )
    out = imdb_genre_year(titles, MAPPING, IMDB_FAMILIES)
    assert out.select("year", "entries", "shorts").rows() == [(1915, 2, 1)]


def test_imdb_mapped_duplicates_and_dropped_genres_weigh_one():
    titles = _titles(
        [
            ("tt1", "movie", 2000, ["Film-Noir", "Crime"]),
            ("tt2", "movie", 2000, ["Sport", "Drama"]),
            ("tt3", "movie", 2000, ["Short", "News"]),
        ]
    )
    out = imdb_genre_year(titles, MAPPING, IMDB_FAMILIES)
    assert dict(out.select("genre", "score").iter_rows()) == {"Crime": 1.0, "Drama": 1.0}
    assert out["entries"].to_list() == [2, 2]
    assert out["share"].sum() == pytest.approx(1.0)


def test_imdb_shares_sum_to_one_per_year():
    titles = _titles(
        [("tt1", "movie", 2000, ["Drama", "Crime"]), ("tt2", "movie", 2001, ["Drama"])]
    )
    out = imdb_genre_year(titles, MAPPING, IMDB_FAMILIES)
    assert out.group_by("year").agg(pl.col("share").sum()).sort("year")["share"].to_list() == [
        1.0,
        1.0,
    ]


def test_imdb_unknown_genre_raises():
    with pytest.raises(ValueError, match="Mime"):
        imdb_genre_year(_titles([("tt1", "movie", 2000, ["Mime"])]), MAPPING, IMDB_FAMILIES)


def test_kobis_as_lumiere_matches_the_lumiere_schema():
    kobis = pl.DataFrame(
        [("tt1", 2020, 5)],
        schema={"imdb_id": pl.String, "year": pl.Int16, "admissions": pl.Int64},
        orient="row",
    ).with_columns(kobis_code=pl.lit("1"), title_ko=pl.lit("x"))
    out = kobis_as_lumiere(kobis)
    expected = _lumiere([]).with_columns(lumiere_id=pl.lit(None, dtype=pl.String)).columns
    assert set(out.columns) == set(expected)
    assert out.schema["lumiere_id"] == pl.String
    assert out.schema["year"] == pl.Int16 and out.schema["admissions"] == pl.Int64
    assert out["market"].to_list() == ["KR"] and out["estimated"].to_list() == [False]


def test_kr_coverage_counts_unmatched_and_other_films_admissions():
    genres = film_genres(_films([("tt1", ["Drama"])]), FAMILIES)
    # 20 distinct films without genres (matched but ungenred), the remainder row (null id)
    rows = [("tt1", 2020, 30), (None, 2020, 10)]
    rows += [(f"tt9{i}", 2020, 10) for i in range(19)] + [("tt1", 2021, 5)]
    kobis = pl.DataFrame(
        rows,
        schema={"imdb_id": pl.String, "year": pl.Int16, "admissions": pl.Int64},
        orient="row",
    )
    out = lumiere_country_genre(kobis_as_lumiere(kobis), genres, {"KR"})
    assert out["year"].unique().to_list() == [2020]  # 2021 has too few films
    assert out["coverage"].to_list() == [pytest.approx(30 / 230)]
    assert out["share"].to_list() == [1.0]
