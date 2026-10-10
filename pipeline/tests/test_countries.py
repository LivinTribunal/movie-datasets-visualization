from pathlib import Path

import polars as pl
import pytest

from movies.reference.countries import COLUMNS, build, name_index

FIXTURES = Path(__file__).parent / "fixtures"

EXTRA = pl.DataFrame(
    {
        "iso2": ["XK"],
        "iso3": ["XKX"],
        "iso_numeric": [""],
        "name": ["Kosovo"],
        "region": ["Europe"],
        "subregion": ["Southern Europe"],
        "region_code": ["150"],
        "subregion_code": ["039"],
    }
)


def _aliases(rows: list[tuple[str, str]]) -> pl.DataFrame:
    return pl.DataFrame(
        {"alias": [a for a, _ in rows], "iso2": [i for _, i in rows], "note": [""] * len(rows)},
        schema={"alias": pl.String, "iso2": pl.String, "note": pl.String},
    )


@pytest.fixture
def iso() -> pl.DataFrame:
    return pl.read_csv(FIXTURES / "countries_iso.csv", infer_schema_length=0)


@pytest.fixture
def table(iso: pl.DataFrame) -> pl.DataFrame:
    aliases = _aliases([("Russia", "RU"), ("Yugoslavia", "RS"), ("Serbia and Montenegro", "RS")])
    return build(iso, EXTRA, aliases)


def test_columns_and_order(table: pl.DataFrame) -> None:
    assert table.columns == [*COLUMNS, "aliases"]
    assert table["iso2"].to_list() == sorted(table["iso2"].to_list())


def test_numeric_keeps_leading_zeros(table: pl.DataFrame) -> None:
    assert table.filter(pl.col("iso2") == "AF")["iso_numeric"].item() == "004"


def test_empty_becomes_null(table: pl.DataFrame) -> None:
    aq = table.filter(pl.col("iso2") == "AQ").row(0, named=True)
    assert aq["region"] is None and aq["subregion_code"] is None
    assert table.filter(pl.col("iso2") == "XK")["iso_numeric"].item() is None


def test_aliases_joined_sorted(table: pl.DataFrame) -> None:
    assert table.filter(pl.col("iso2") == "RS")["aliases"].item() == (
        "Serbia and Montenegro|Yugoslavia"
    )
    assert table.filter(pl.col("iso2") == "DE")["aliases"].item() is None


def test_extra_appended(table: pl.DataFrame) -> None:
    assert table.filter(pl.col("iso2") == "XK")["name"].item() == "Kosovo"


def test_name_index(table: pl.DataFrame) -> None:
    idx = dict(name_index(table).iter_rows())
    assert idx["Russia"] == "RU"
    assert idx["Germany"] == "DE"
    assert idx["Kosovo"] == "XK"


def test_alias_unknown_iso2(iso: pl.DataFrame) -> None:
    with pytest.raises(ValueError, match="unknown iso2"):
        build(iso, EXTRA, _aliases([("Atlantis", "ZZ")]))


def test_duplicate_alias(iso: pl.DataFrame) -> None:
    with pytest.raises(ValueError, match="duplicate aliases"):
        build(iso, EXTRA, _aliases([("Russia", "RU"), ("Russia", "RS")]))
