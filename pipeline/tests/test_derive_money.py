from datetime import date

import polars as pl

from movies.derive.money import money, wikidata_pick

CURRENCIES = pl.DataFrame(
    [
        ("Q4917", "USD", "US", None, None),
        ("Q4916", "EUR", "DE", 1999, None),
        ("Q16068", "DEM", "DE", None, 1998),
    ],
    schema={
        "currency_qid": pl.String,
        "code": pl.String,
        "fx_iso2": pl.String,
        "valid_from": pl.Int16,
        "valid_to": pl.Int16,
    },
    orient="row",
)
FX = pl.DataFrame(
    [("DE", 2010, 0.8), ("DE", 1990, 2.0), ("US", 2010, 1.0)],
    schema={"iso2": pl.String, "year": pl.Int16, "lcu_per_usd": pl.Float64},
    orient="row",
)
CPI = pl.DataFrame(
    [(1990, 100.0), (2000, 150.0), (2010, 200.0), (2025, 300.0)],
    schema={"year": pl.Int16, "cpi": pl.Float64},
    orient="row",
)
WIKI_SCHEMA = {
    "imdb_id": pl.String,
    "property": pl.String,
    "amount": pl.Float64,
    "unit_qid": pl.String,
    "point_in_time": pl.Date,
    "place_qid": pl.String,
    "rank": pl.String,
}


def _wiki(rows: list[tuple]) -> pl.DataFrame:
    return pl.DataFrame(rows, schema=WIKI_SCHEMA, orient="row")


def _films(rows: list[tuple]) -> pl.DataFrame:
    """(imdb_id, year, numbers_budget, budget, numbers_worldwide_gross, revenue)"""
    return pl.DataFrame(
        rows,
        schema={
            "imdb_id": pl.String,
            "year": pl.Int16,
            "numbers_budget": pl.Float64,
            "budget": pl.Float64,
            "numbers_worldwide_gross": pl.Float64,
            "revenue": pl.Float64,
        },
        orient="row",
    )


def _run(films: list[tuple], wiki: list[tuple] | None = None) -> dict:
    out = money(_films(films), _wiki(wiki or []), CURRENCIES, FX, CPI)
    return out.row(0, named=True)


def test_source_order_numbers_then_tmdb_then_wikidata() -> None:
    row = _run(
        [("tt1", 2010, 5e6, 6e6, None, 9e6)],
        [("tt1", "box_office", 8e6, "Q4917", None, None, "normal")],
    )
    assert (row["budget"], row["budget_src"]) == (5e6, "numbers")
    assert (row["revenue"], row["revenue_src"]) == (9e6, "tmdb")


def test_sources_are_chosen_per_field() -> None:
    row = _run(
        [("tt1", 2010, None, 6e6, None, None)],
        [("tt1", "box_office", 8e6, "Q4917", None, None, "normal")],
    )
    assert (row["budget_src"], row["revenue_src"]) == ("tmdb", "wikidata")
    assert row["revenue_currency"] == "USD"


def test_all_null_gives_null_value_currency_and_src() -> None:
    row = _run([("tt1", 2010, None, None, None, None)])
    assert row["budget"] is None and row["budget_currency"] is None and row["budget_src"] is None
    assert row["budget_usd"] is None and row["budget_disagree"] is False


def test_wikidata_pick_usd_beats_eur_and_preferred_beats_normal() -> None:
    wiki = _wiki(
        [
            ("tt1", "budget", 1e6, "Q4916", None, None, "preferred"),
            ("tt1", "budget", 2e6, "Q4917", None, None, "normal"),
            ("tt2", "budget", 3e6, "Q4917", None, None, "normal"),
            ("tt2", "budget", 4e6, "Q4917", None, None, "preferred"),
        ]
    )
    got = {
        r["imdb_id"]: (r["amount"], r["currency"])
        for r in wikidata_pick(wiki, CURRENCIES).to_dicts()
    }
    assert got == {"tt1": (2e6, "USD"), "tt2": (4e6, "USD")}


def test_wikidata_pick_latest_then_largest_and_null_dates_last() -> None:
    wiki = _wiki(
        [
            ("tt1", "budget", 9e6, "Q4917", None, None, "normal"),
            ("tt1", "budget", 1e6, "Q4917", date(2001, 1, 1), None, "normal"),
            ("tt1", "budget", 2e6, "Q4917", date(2005, 1, 1), None, "normal"),
        ]
    )
    assert wikidata_pick(wiki, CURRENCIES)["amount"].to_list() == [2e6]


def test_wikidata_pick_ignores_domestic_box_office_and_non_money_units() -> None:
    wiki = _wiki(
        [
            ("tt1", "box_office", 5e6, "Q4917", None, "Q30", "normal"),
            ("tt1", "box_office", 7e6, "Q4917", None, "Q13780930", "normal"),
            ("tt2", "box_office", 5e6, "Q4917", None, "Q30", "normal"),
            ("tt3", "budget", 5e6, "Q11190", None, None, "normal"),
        ]
    )
    got = wikidata_pick(wiki, CURRENCIES)
    assert got.rows() == [("tt1", "box_office", 7e6, "USD")]


def test_eur_converts_with_germany_rate() -> None:
    row = _run(
        [("tt1", 2010, None, None, None, None)],
        [("tt1", "budget", 8e6, "Q4916", None, None, "normal")],
    )
    assert row["budget_src"] == "wikidata" and row["budget_currency"] == "EUR"
    assert row["budget_usd"] == 8e6 / 0.8


def test_dem_converts_with_germany_rate_in_1990() -> None:
    row = _run(
        [("tt1", 1990, None, None, None, None)],
        [("tt1", "budget", 8e6, "Q16068", None, None, "normal")],
    )
    assert row["budget_usd"] == 4e6


def test_eur_amount_before_1999_is_null_but_nominal_kept() -> None:
    row = _run(
        [("tt1", 1990, None, None, None, None)],
        [("tt1", "budget", 8e6, "Q4916", None, None, "normal")],
    )
    assert row["budget_usd"] is None and row["budget_usd2025"] is None
    assert (row["budget"], row["budget_currency"]) == (8e6, "EUR")


def test_cpi_adjusts_to_2025() -> None:
    row = _run([("tt1", 2000, 1e6, None, None, None)])
    assert row["budget_usd2025"] == 1e6 * 300.0 / 150.0


def test_year_before_cpi_has_usd_but_no_usd2025() -> None:
    row = _run([("tt1", 1940, 1e6, None, None, None)])
    assert row["budget_usd"] == 1e6 and row["budget_usd2025"] is None


def test_disagreement_threshold() -> None:
    assert _run([("tt1", 2010, 100_000.0, 130_000.0, None, None)])["budget_disagree"] is True
    assert _run([("tt1", 2010, 100_000.0, 120_000.0, None, None)])["budget_disagree"] is False
    assert _run([("tt1", 2010, 100_000.0, None, None, None)])["budget_disagree"] is False


def test_disagreement_compares_converted_wikidata() -> None:
    row = _run(
        [("tt1", 2010, 100_000.0, None, None, None)],
        [("tt1", "budget", 80_000.0, "Q4916", None, None, "normal")],
    )
    assert row["budget_disagree"] is False  # 80 EUR / 0.8 = 100 USD
    row = _run(
        [("tt1", 2010, 100_000.0, None, None, None)],
        [("tt1", "budget", 160_000.0, "Q4916", None, None, "normal")],
    )
    assert row["budget_disagree"] is True  # 200 USD


def test_roi_needs_a_budget_of_at_least_100k() -> None:
    assert _run([("tt1", 2010, 50_000.0, None, 500_000.0, None)])["roi"] is None
    assert _run([("tt1", 2010, 100_000.0, None, 500_000.0, None)])["roi"] == 5.0


def test_profit_is_null_when_a_side_is_missing() -> None:
    assert _run([("tt1", 2010, 1e6, None, None, None)])["profit_usd2025"] is None
    row = _run([("tt1", 2010, 1e6, None, 3e6, None)])
    assert row["profit_usd2025"] == 2e6 * 300.0 / 200.0


def test_tiny_numbers_value_is_dropped_before_the_pick() -> None:
    row = _run([("tt1", 2010, None, None, 401.0, 2e6)])
    assert (row["revenue"], row["revenue_src"]) == (2e6, "tmdb")


def test_only_a_tiny_value_gives_null_revenue_and_src() -> None:
    row = _run([("tt1", 2010, None, None, 401.0, None)])
    assert row["revenue"] is None and row["revenue_src"] is None


def test_tiny_converted_wikidata_budget_is_dropped() -> None:
    wiki = [("tt1", "budget", 500.0, "Q4916", None, None, "normal")]
    row = _run([("tt1", 2010, None, None, None, None)], wiki)
    assert row["budget"] is None and row["budget_src"] is None and row["budget_currency"] is None


def test_tiny_usd_wikidata_budget_does_not_shadow_a_valid_eur_one() -> None:
    wiki = [
        ("tt1", "budget", 500.0, "Q4917", None, None, "normal"),
        ("tt1", "budget", 8e6, "Q4916", None, None, "normal"),
    ]
    row = _run([("tt1", 2010, None, None, None, None)], wiki)
    assert (row["budget"], row["budget_currency"], row["budget_src"]) == (8e6, "EUR", "wikidata")


def test_unconvertible_tiny_wikidata_budget_is_dropped() -> None:
    wiki = [("tt1", "budget", 500.0, "Q4916", None, None, "normal")]
    row = _run([("tt1", 1990, None, None, None, None)], wiki)
    assert row["budget"] is None and row["budget_currency"] is None and row["budget_src"] is None


def test_one_row_per_film() -> None:
    films = _films([("tt1", 2010, 1e6, None, None, None), ("tt2", 2010, None, None, None, None)])
    out = money(films, _wiki([]), CURRENCIES, FX, CPI)
    assert out["imdb_id"].to_list() == ["tt1", "tt2"]
