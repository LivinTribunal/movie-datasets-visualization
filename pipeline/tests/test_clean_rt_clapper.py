from pathlib import Path

import polars as pl

from movies.clean.rt_clapper import clean

FIXTURES = Path(__file__).parent / "fixtures"


def _clean() -> pl.DataFrame:
    return clean(pl.read_csv(FIXTURES / "rt_clapper_sample.csv", infer_schema=False))


def test_box_office_suffixes() -> None:
    by_id = dict(zip(_clean()["rt_id"], _clean()["box_office_usd"], strict=True))
    assert by_id["m/big_movie"] == 31_400_000.0
    assert by_id["m/small_movie"] == 11_500.0
    assert by_id["m/giant_movie"] == 1_200_000_000.0
    assert by_id["m/plain_movie"] == 500.0
    assert by_id["m/space-zombie-bingo"] is None


def test_rt_id_prefix_and_types() -> None:
    out = _clean()
    assert out["rt_id"].str.starts_with("m/").all()
    assert out.schema["tomatometer"] == pl.Int8
    assert out.schema["release_date_theaters"] == pl.Date
    assert out.schema["runtime"] == pl.Int16


def test_duplicate_id_keeps_row_with_scores() -> None:
    out = _clean().filter(pl.col("rt_id") == "m/dup_movie")
    assert out.height == 1
    assert out["tomatometer"][0] == 75
    assert out["audience_score"][0] == 60


def test_genres_list_and_empty_is_null() -> None:
    by_id = dict(zip(_clean()["rt_id"], _clean()["genres"], strict=True))
    assert by_id["m/space-zombie-bingo"].to_list() == ["Comedy", "Horror", "Sci-fi"]
    assert by_id["m/small_movie"] is None
