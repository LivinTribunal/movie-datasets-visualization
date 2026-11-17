import polars as pl

from movies.clean.unesco import clean

COUNTRIES = pl.DataFrame({"iso2": ["CZ", "SK"], "iso3": ["CZE", "SVK"]})


def _series(country: str, indicator: str, periods: list[str], values: list) -> dict:
    dims = {"country": country, "freq": "A", "indicator": indicator}
    return {"dimensions": dims, "period": periods, "value": values}


PAYLOAD = {
    "series": {
        "docs": [
            _series("CZE", "220063", ["2010", "2011", "2012"], [100.0, 200.0, "NA"]),
            _series("CZE", "220223", ["2010", "2011"], [40.0, 250.0]),
            _series("SVK", "220063", ["2010"], [50.0]),
            _series("SVK", "220063", ["2011"], [0.0]),
            _series("ANT", "220063", ["2010"], [9.0]),
        ]
    }
}


def test_maps_iso3_drops_unknown_and_na() -> None:
    out = clean(PAYLOAD, COUNTRIES)
    assert out["country_iso2"].to_list() == ["CZ", "CZ", "SK"]
    assert out["year"].to_list() == [2010, 2011, 2010]


def test_national_above_total_is_dropped() -> None:
    out = clean(PAYLOAD, COUNTRIES)
    assert out["admissions_national"].to_list() == [40.0, None, None]


def test_total_only_year_keeps_null_national() -> None:
    out = clean(PAYLOAD, COUNTRIES)
    assert out.filter(pl.col("country_iso2") == "SK").row(0) == ("SK", 2010, 50.0, None)


def test_zero_total_is_null_and_row_dropped() -> None:
    assert ("SK", 2011) not in clean(PAYLOAD, COUNTRIES).select("country_iso2", "year").rows()


def test_dtypes() -> None:
    assert clean(PAYLOAD, COUNTRIES).schema == {
        "country_iso2": pl.String,
        "year": pl.Int16,
        "admissions": pl.Float64,
        "admissions_national": pl.Float64,
    }
