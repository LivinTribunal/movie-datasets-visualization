import json
from pathlib import Path

import polars as pl
import pytest

from movies.export.app import films_table, franchises_table, genre_year, to_columns
from movies.validate.app import check
from test_export_app import FILM_GENRES, FILMS, FRANCHISES, MONEY, RATINGS

COUNTRY_GENRE = pl.DataFrame(
    {
        "source": ["netflix"] * 2,
        "country_iso2": ["US"] * 2,
        "year": [2024] * 2,
        "genre": ["Drama", "Comedy"],
        "family": ["Drama", "Comedy"],
        "share": [0.6, 0.4],
        "score": [6.0, 4.0],
        "coverage": [0.8, 0.8],
        "fuzzy_share": [0.1, 0.1],
        "estimated_share": [0.0, 0.0],
    }
)
COUNTRIES = pl.DataFrame(
    {
        "iso2": ["US", "CZ"],
        "iso_numeric": ["840", "203"],
        "name": ["United States", "Czechia"],
        "region": ["Americas", "Europe"],
        "subregion": ["Northern America", "Eastern Europe"],
    }
)
FAMILIES = pl.DataFrame(
    {
        "genre": ["Drama", "Comedy"],
        "family": ["Drama", "Comedy"],
        "family_order": [1, 2],
        "colour": ["#000000", "#ffffff"],
    }
)


def _write(path: Path, **overrides: pl.DataFrame) -> None:
    tables = {
        "films.json": films_table(FILMS, MONEY, RATINGS, FILM_GENRES),
        "genre_year.json": genre_year(FILMS, MONEY, FILM_GENRES),
        "country_genre.json": COUNTRY_GENRE,
        "countries.json": COUNTRIES,
        "genre_families.json": FAMILIES,
        "franchises.json": franchises_table(FRANCHISES),
    }
    for name, df in tables.items():
        df = overrides.get(name.removesuffix(".json"), df)
        (path / name).write_text(json.dumps({"columns": to_columns(df)}))
    (path / "countries.topo.json").write_text("{}")
    (path / "meta.json").write_text("{}")


def test_valid_dir_has_no_errors(tmp_path):
    _write(tmp_path)
    assert check(tmp_path) == []


def _errors_with(tmp_path, **overrides: pl.DataFrame) -> list[str]:
    _write(tmp_path, **overrides)
    return check(tmp_path)


def test_duplicate_imdb_id(tmp_path):
    films = films_table(FILMS, MONEY, RATINGS, FILM_GENRES)
    errors = _errors_with(tmp_path, films=pl.concat([films, films.head(1)]))
    assert any("duplicate imdb_id" in e for e in errors)


def test_rating_out_of_range(tmp_path):
    films = films_table(FILMS, MONEY, RATINGS, FILM_GENRES).with_columns(imdb_100=pl.lit(101.0))
    assert any("imdb_100 outside" in e for e in _errors_with(tmp_path, films=films))


def test_unknown_family(tmp_path):
    cg = COUNTRY_GENRE.with_columns(family=pl.lit("Western"))
    assert any("unknown family" in e for e in _errors_with(tmp_path, country_genre=cg))


def test_unknown_country(tmp_path):
    cg = COUNTRY_GENRE.with_columns(country_iso2=pl.lit("XX"))
    assert any("unknown country" in e for e in _errors_with(tmp_path, country_genre=cg))


def test_shares_not_summing_to_one(tmp_path):
    cg = COUNTRY_GENRE.with_columns(share=pl.Series([0.5, 0.4]))
    assert any("do not sum to 1" in e for e in _errors_with(tmp_path, country_genre=cg))


def test_missing_file(tmp_path):
    _write(tmp_path)
    (tmp_path / "films.json").unlink()
    assert "films.json: file missing" in check(tmp_path)


def test_wrong_columns(tmp_path):
    _write(tmp_path)
    (tmp_path / "countries.json").write_text('{"columns": {"iso2": []}}')
    assert any("countries.json: columns" in e for e in check(tmp_path))


@pytest.mark.parametrize("name", ["country_genre"])
def test_fuzzy_share_above_coverage(tmp_path, name):
    cg = COUNTRY_GENRE.with_columns(fuzzy_share=pl.lit(0.9))
    assert any("exceeds coverage" in e for e in _errors_with(tmp_path, **{name: cg}))


def test_estimated_share_outside_range(tmp_path):
    cg = COUNTRY_GENRE.with_columns(estimated_share=pl.lit(1.5))
    assert any("estimated_share outside 0-1" in e for e in _errors_with(tmp_path, country_genre=cg))


def test_null_list_column(tmp_path):
    films = films_table(FILMS, MONEY, RATINGS, FILM_GENRES).with_columns(
        countries=pl.lit(None, dtype=pl.List(pl.String))
    )
    assert any("countries has nulls" in e for e in _errors_with(tmp_path, films=films))


def test_franchise_installment_beyond_n_released(tmp_path):
    bad = FRANCHISES.with_columns(installment=pl.Series([2, 4, 1]))
    errors = _errors_with(tmp_path, franchises=franchises_table(bad))
    assert any("installment" in e for e in errors)


def test_franchise_small_collection_and_bad_rating(tmp_path):
    bad = FRANCHISES.with_columns(
        n_released=pl.Series([2, 2, 2]), imdb_100=pl.Series([70.0, 101.0, None])
    )
    errors = _errors_with(tmp_path, franchises=franchises_table(bad))
    assert any("n_released" in e for e in errors)
    assert any("imdb_100 outside" in e for e in errors)
