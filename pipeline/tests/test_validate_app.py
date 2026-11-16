import json
from pathlib import Path

import polars as pl
import pytest

from movies.derive.extras import DETAIL_COLUMNS
from movies.export.app import (
    ATTRIBUTION,
    SOURCES,
    country_tables,
    films_table,
    franchises_table,
    to_columns,
    write_country_tables,
    write_detail,
    write_films,
    write_franchises,
)
from movies.export.pack import str_col, write_pack
from movies.validate import app as validate_app
from movies.validate.app import check
from test_export_app import EXTRAS, FILM_GENRES, FILMS, FRANCHISES, MONEY, RATINGS, _shares

GENRES = ["Comedy", "Drama"]
FAMILIES = ["Comedy", "Drama"]
COUNTRY_CODES = ["CZ", "US"]
COUNTRIES = pl.DataFrame(
    {
        "iso2": ["US", "CZ"],
        "iso_numeric": ["840", "203"],
        "name": ["United States", "Czechia"],
        "region": ["Americas", "Europe"],
        "subregion": ["Northern America", "Eastern Europe"],
    }
)
FAMILY_TABLE = pl.DataFrame(
    {
        "genre": GENRES,
        "family": FAMILIES,
        "family_order": [1, 2],
        "colour": ["#000000", "#ffffff"],
    }
)
META = {
    "snapshots": {"tmdb_imdb": "2026-10-01", "netflix": "2026-09-27"},
    "base_year": 2025,
    "counts": {"films": 4},
    "detail": {"shard_size": 1000, "shards": 1},
    "notes": ["note"],
    "attribution": ATTRIBUTION,
    "sources": SOURCES,
}


def _films() -> pl.DataFrame:
    return films_table(FILMS, MONEY, RATINGS, FILM_GENRES, FRANCHISES, EXTRAS)


def _franchises(df: pl.DataFrame = FRANCHISES) -> pl.DataFrame:
    return franchises_table(df, _films(), FILM_GENRES, FAMILIES)


def _country_frames() -> tuple[pl.DataFrame, pl.DataFrame]:
    sources = [
        (
            "netflix",
            "chart_score",
            pl.concat([_shares("CZ", 2025, "Drama"), _shares("CZ", 2025, "Comedy")]),
        ),
        ("cinema", "gross_usd", _shares("US", 2024, "Comedy")),
    ]
    return country_tables(sources, GENRES)


def _write(
    path: Path,
    *,
    films: pl.DataFrame | None = None,
    genres: list[str] = GENRES,
    franchises: pl.DataFrame | None = None,
    country_genre: pl.DataFrame | None = None,
    country_year: pl.DataFrame | None = None,
    countries: pl.DataFrame = COUNTRIES,
    families: pl.DataFrame = FAMILY_TABLE,
    meta: dict | None = None,
) -> None:
    films = _films() if films is None else films
    write_films(
        films,
        genres,
        FAMILIES,
        COUNTRY_CODES,
        path / "films.pack",
        path / "films_text.pack",
        path / "films_poster.pack",
    )
    detail = films.select("imdb_id").join(
        EXTRAS.select("imdb_id", *DETAIL_COLUMNS), on="imdb_id", how="left"
    )
    write_detail(detail, int(films["notable"].sum()), path)
    cg, cy = _country_frames()
    write_country_tables(
        cg if country_genre is None else country_genre,
        cy if country_year is None else country_year,
        GENRES,
        COUNTRY_CODES,
        path / "country_genre.pack",
        path / "country_year.pack",
    )
    write_franchises(_franchises() if franchises is None else franchises, path / "franchises.pack")
    (path / "countries.json").write_text(json.dumps({"columns": to_columns(countries)}))
    (path / "genre_families.json").write_text(json.dumps({"columns": to_columns(families)}))
    (path / "countries.topo.json").write_text("{}")
    (path / "meta.json").write_text(json.dumps(META if meta is None else meta))


def _errors(tmp_path: Path, **overrides) -> list[str]:
    _write(tmp_path, **overrides)
    return check(tmp_path)


def _has(errors: list[str], name: str, rule: str) -> bool:
    return any(e.startswith(f"{name}:") and rule in e for e in errors)


def test_valid_dir_has_no_errors(tmp_path):
    assert _errors(tmp_path) == []


def test_missing_file(tmp_path):
    _write(tmp_path)
    (tmp_path / "films.pack").unlink()
    assert "films.pack: file missing" in check(tmp_path)


def test_wrong_columns(tmp_path):
    _write(tmp_path)
    (tmp_path / "countries.json").write_text('{"columns": {"iso2": []}}')
    write_pack(tmp_path / "films_text.pack", 1, {}, [str_col("x", pl.Series(["a"]))])
    errors = check(tmp_path)
    assert _has(errors, "countries.json", "columns")
    assert _has(errors, "films_text.pack", "columns")


def test_unreadable_pack_is_one_error(tmp_path):
    _write(tmp_path)
    (tmp_path / "films_poster.pack").write_bytes(b"not a pack")
    assert _has(check(tmp_path), "films_poster.pack", "unreadable")


def test_duplicate_imdb(tmp_path):
    films = _films().with_columns(imdb_id=pl.Series(["tt1", "tt1", "tt3", "tt4"]))
    assert _has(_errors(tmp_path, films=films), "films.pack", "duplicate imdb")


def test_year_outside_range(tmp_path):
    films = _films().with_columns(year=pl.Series([1899, 2000, 2000, 2001], dtype=pl.Int16))
    assert _has(_errors(tmp_path, films=films), "films.pack", "year outside 1900-2026")


def test_votes_increase_down_the_rows(tmp_path):
    films = _films().with_columns(imdb_votes=pl.Series([1000, 3000, 2000, 1500]))
    assert _has(_errors(tmp_path, films=films), "films.pack", "imdb_votes increases")


def test_meta_notable_must_be_positive(tmp_path):
    films = _films().with_columns(notable=pl.lit(False))
    assert _has(_errors(tmp_path, films=films), "films.pack", "meta.notable")


def test_last_notable_row_needs_10000_votes(tmp_path):
    films = _films().with_columns(notable=pl.Series([True, True, False, False]))
    assert _has(_errors(tmp_path, films=films), "films.pack", "last notable row")


def test_row_after_notable_rows_needs_fewer_votes(tmp_path):
    films = _films().with_columns(imdb_votes=pl.Series([50000, 20000, 3000, 1500]))
    assert _has(_errors(tmp_path, films=films), "films.pack", "row after the notable rows")


def test_rating_out_of_range(tmp_path):
    films = _films().with_columns(tomatometer_100=pl.lit(101.0))
    assert _has(_errors(tmp_path, films=films), "films.pack", "tomatometer_100 outside 0-100")


def test_gap_out_of_range(tmp_path):
    films = _films().with_columns(gap=pl.lit(101.0))
    assert _has(_errors(tmp_path, films=films), "films.pack", "gap outside -100..100")


@pytest.mark.parametrize(
    "col", ["budget_usd", "budget_usd2025", "revenue_usd", "revenue_usd2025", "roi"]
)
def test_negative_money(tmp_path, col):
    films = _films().with_columns(pl.lit(-1.0).alias(col))
    assert _has(_errors(tmp_path, films=films), "films.pack", f"negative {col}")


def test_bad_money_source(tmp_path, monkeypatch):
    monkeypatch.setattr(validate_app, "SRC_VALUES", {"numbers", None})
    assert _has(_errors(tmp_path), "films.pack", "bad revenue_src")


def test_unknown_country_in_films(tmp_path):
    errors = _errors(tmp_path, countries=COUNTRIES.filter(pl.col("iso2") != "CZ"))
    assert _has(errors, "films.pack", "unknown country ['CZ']")


def test_meta_genres_must_match_genre_families(tmp_path):
    errors = _errors(tmp_path, families=FAMILY_TABLE.with_columns(genre=pl.Series(GENRES[::-1])))
    assert _has(errors, "films.pack", "meta.genres")


def test_meta_families_must_follow_family_order(tmp_path):
    errors = _errors(tmp_path, families=FAMILY_TABLE.with_columns(family_order=pl.Series([2, 1])))
    assert _has(errors, "films.pack", "meta.families")


def test_genre_mask_beyond_genre_list(tmp_path):
    films = _films().with_columns(genres=pl.Series([["Horror"], ["Comedy"], ["Drama"], ["Drama"]]))
    errors = _errors(tmp_path, films=films, genres=[*GENRES, "Horror"])
    assert _has(errors, "films.pack", "genre_mask has a bit beyond")


def test_family_mask_must_follow_genre_mask(tmp_path):
    films = _films().with_columns(
        families=pl.Series([["Comedy"], ["Comedy"], ["Drama"], ["Drama"]])
    )
    assert _has(_errors(tmp_path, films=films), "films.pack", "family_mask")


def test_installment_null_exactly_when_collection_id_null(tmp_path):
    films = _films().with_columns(installment=pl.Series([None, 2, None, None], dtype=pl.Int64))
    assert _has(_errors(tmp_path, films=films), "films.pack", "installment is null")


def test_collection_id_must_be_in_franchises(tmp_path):
    films = _films().with_columns(collection_id=pl.Series([7, 7, 99, None], dtype=pl.Int64))
    films = films.with_columns(installment=pl.Series([1, 2, 1, None], dtype=pl.Int64))
    assert _has(_errors(tmp_path, films=films), "films.pack", "collection_id not in franchises")


def test_text_pack_needs_the_same_rows(tmp_path):
    _write(tmp_path)
    cols = [str_col("title", pl.Series(["a", "b", "c"])), str_col("director", pl.Series([""] * 3))]
    write_pack(tmp_path / "films_text.pack", 3, {}, cols)
    assert _has(check(tmp_path), "films_text.pack", "3 rows != 4 rows")


def test_text_pack_title_has_no_nulls(tmp_path):
    _write(tmp_path)
    cols = [
        str_col("title", pl.Series(["A", None, "C", "D"])),
        str_col("director", pl.Series([""] * 4)),
    ]
    write_pack(tmp_path / "films_text.pack", 4, {}, cols)
    assert _has(check(tmp_path), "films_text.pack", "title has nulls")


def test_poster_pack_needs_the_same_rows(tmp_path):
    _write(tmp_path)
    write_pack(tmp_path / "films_poster.pack", 2, {}, [str_col("poster", pl.Series(["a", "b"]))])
    assert _has(check(tmp_path), "films_poster.pack", "2 rows != 4 rows")


def test_franchise_installment_beyond_n_released(tmp_path):
    bad = FRANCHISES.with_columns(installment=pl.Series([2, 4, 1]))
    errors = _errors(tmp_path, franchises=_franchises(bad))
    assert _has(errors, "franchises.pack", "installment outside 1..n_released")


def test_franchise_small_collection_and_bad_rating(tmp_path):
    bad = FRANCHISES.with_columns(
        n_released=pl.Series([2, 2, 2]), imdb_100=pl.Series([70.0, 101.0, None])
    )
    errors = _errors(tmp_path, franchises=_franchises(bad))
    assert _has(errors, "franchises.pack", "n_released under 3")
    assert _has(errors, "franchises.pack", "imdb_100 outside 0-100")


def test_franchise_installments_must_be_exactly_1_to_n(tmp_path):
    bad = FRANCHISES.with_columns(installment=pl.Series([2, 2, 1]))
    errors = _errors(tmp_path, franchises=_franchises(bad))
    assert _has(errors, "franchises.pack", "not exactly 1..n_released")


def test_franchise_first_installment_imdb_vs_first_must_be_zero(tmp_path):
    bad = FRANCHISES.with_columns(imdb_100_vs_first=pl.Series([-9.96, 2.0, None]))
    errors = _errors(tmp_path, franchises=_franchises(bad))
    assert _has(errors, "franchises.pack", "imdb_100_vs_first not 0")


def test_franchise_revenue_vs_first_not_negative(tmp_path):
    bad = FRANCHISES.with_columns(revenue_vs_first=pl.Series([-0.5, None, None]))
    assert _has(_errors(tmp_path, franchises=_franchises(bad)), "franchises.pack", "negative")


def test_franchise_film_row_must_be_a_part_of_the_collection(tmp_path):
    bad = _franchises().with_columns(film_row=pl.Series([2, 1, None], dtype=pl.UInt32))
    assert _has(_errors(tmp_path, franchises=bad), "franchises.pack", "film_row")


def test_franchise_film_row_beyond_films(tmp_path):
    bad = _franchises().with_columns(film_row=pl.Series([9, 1, None], dtype=pl.UInt32))
    assert _has(_errors(tmp_path, franchises=bad), "franchises.pack", "film_row")


def test_unknown_country_source(tmp_path):
    cg, cy = _country_frames()
    errors = _errors(
        tmp_path,
        country_genre=cg.with_columns(source=pl.lit("hbo")),
        country_year=cy.with_columns(source=pl.lit("hbo")),
    )
    assert _has(errors, "country_genre.pack", "unknown source")
    assert _has(errors, "country_year.pack", "unknown source")


def test_country_not_in_countries_json(tmp_path):
    errors = _errors(tmp_path, countries=COUNTRIES.filter(pl.col("iso2") != "US"))
    assert _has(errors, "country_genre.pack", "unknown country ['US']")
    assert _has(errors, "country_year.pack", "unknown country ['US']")


def test_genre_beyond_genre_count(tmp_path):
    cg, _ = _country_frames()
    errors = _errors(tmp_path, country_genre=cg.with_columns(genre=pl.lit(5, dtype=pl.UInt8)))
    assert _has(errors, "country_genre.pack", "genre beyond")


def test_negative_score(tmp_path):
    cg, _ = _country_frames()
    assert _has(
        _errors(tmp_path, country_genre=cg.with_columns(score=pl.lit(-1.0))),
        "country_genre.pack",
        "negative score",
    )


def test_duplicate_country_genre_key(tmp_path):
    cg, _ = _country_frames()
    errors = _errors(tmp_path, country_genre=pl.concat([cg, cg.head(1)]))
    assert _has(errors, "country_genre.pack", "duplicate key")


def test_duplicate_country_year_key(tmp_path):
    _, cy = _country_frames()
    errors = _errors(tmp_path, country_year=pl.concat([cy, cy.head(1)]))
    assert _has(errors, "country_year.pack", "duplicate key")


def test_packs_hold_different_source_country_years(tmp_path):
    _, cy = _country_frames()
    errors = _errors(tmp_path, country_year=cy.head(1))
    assert _has(errors, "country_genre.pack / country_year.pack", "different source-country-years")


@pytest.mark.parametrize("col", ["coverage", "estimated_share"])
def test_share_outside_range(tmp_path, col):
    _, cy = _country_frames()
    errors = _errors(tmp_path, country_year=cy.with_columns(pl.lit(1.5).alias(col)))
    assert _has(errors, "country_year.pack", f"{col} outside 0-1")


def test_fuzzy_share_above_coverage(tmp_path):
    _, cy = _country_frames()
    errors = _errors(tmp_path, country_year=cy.with_columns(fuzzy_share=pl.lit(0.9)))
    assert _has(errors, "country_year.pack", "fuzzy_share exceeds coverage")


def test_entries_under_one(tmp_path):
    _, cy = _country_frames()
    errors = _errors(tmp_path, country_year=cy.with_columns(entries=pl.lit(0, dtype=pl.UInt32)))
    assert _has(errors, "country_year.pack", "entries under 1")


def test_unknown_measure(tmp_path, monkeypatch):
    monkeypatch.setattr(validate_app, "MEASURES", {"films"})
    assert _has(_errors(tmp_path), "country_year.pack", "unknown measure")


@pytest.mark.parametrize(
    "key", ["snapshots", "base_year", "counts", "notes", "attribution", "sources"]
)
def test_meta_missing_key(tmp_path, key):
    meta = {k: v for k, v in META.items() if k != key}
    assert _has(_errors(tmp_path, meta=meta), "meta.json", f"missing {key}")


def test_meta_attribution_not_empty(tmp_path):
    assert _has(_errors(tmp_path, meta={**META, "attribution": []}), "meta.json", "attribution")


def test_meta_sources_exactly_three_keys(tmp_path):
    meta = {**META, "sources": {"netflix": "x", "cinema": "y"}}
    assert _has(_errors(tmp_path, meta=meta), "meta.json", "sources keys")


def test_file_over_its_size_limit(tmp_path, monkeypatch):
    monkeypatch.setitem(validate_app.LIMITS, "films.pack", 10)
    errors = _errors(tmp_path)
    assert _has(errors, "films.pack", "MB over the 0.0 MB limit")


def test_directory_over_total_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(validate_app, "TOTAL_LIMIT", 10)
    assert _has(_errors(tmp_path), "app data", "MB over the 0.0 MB limit")


@pytest.mark.parametrize("name", validate_app.STALE)
def test_stale_file(tmp_path, name):
    _write(tmp_path)
    (tmp_path / name).write_text("{}")
    assert _has(check(tmp_path), name, "stale file")


def test_detail_shard_missing(tmp_path):
    meta = META | {"detail": {"shard_size": 1000, "shards": 2}}
    assert _has(_errors(tmp_path, meta=meta), "films_detail_1.pack", "file missing")


def test_detail_shard_wrong_size(tmp_path):
    meta = META | {"detail": {"shard_size": 1000, "shards": 2}}
    assert _has(_errors(tmp_path, meta=meta), "films_detail_0.pack", "1 rows, expected 1000")


def test_detail_rows_must_equal_notable(tmp_path):
    films = _films().with_columns(notable=pl.Series([True, True, False, False]))
    _write(tmp_path)
    write_detail(films.select("imdb_id").join(EXTRAS, on="imdb_id"), 1, tmp_path)
    errors = check(tmp_path)
    assert errors == []
    write_detail(films.select("imdb_id").join(EXTRAS, on="imdb_id"), 2, tmp_path)
    assert _has(check(tmp_path), "films_detail_*.pack", "!= 1 notable")


def test_detail_shard_over_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(validate_app, "DETAIL_LIMIT", 10)
    assert _has(_errors(tmp_path), "films_detail_0.pack", "over the")


def test_meta_without_detail(tmp_path):
    meta = {k: v for k, v in META.items() if k != "detail"}
    assert _has(_errors(tmp_path, meta=meta), "meta.json", "detail")


def test_bad_dict_value(tmp_path, monkeypatch):
    monkeypatch.setitem(validate_app.DICT_VALUES, "studio", {None})
    assert _has(_errors(tmp_path), "films.pack", "bad studio")


def test_oscar_noms_under_wins(tmp_path):
    films = _films().with_columns(oscar_noms=pl.Series([0, 0, None, None], dtype=pl.Int16))
    assert _has(_errors(tmp_path, films=films), "films.pack", "oscar_noms under oscar_wins")


def test_negative_extra_money(tmp_path):
    films = _films().with_columns(opening_usd=pl.lit(-1.0))
    assert _has(_errors(tmp_path, films=films), "films.pack", "negative opening_usd")
