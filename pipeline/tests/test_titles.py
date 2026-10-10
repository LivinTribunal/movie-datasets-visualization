import polars as pl
from rapidfuzz import fuzz

from movies.join.titles import apply_overrides, match, normalise


def _left(rows: list[tuple[str, str, int, int]]) -> pl.DataFrame:
    return pl.DataFrame(
        rows,
        schema={
            "key": pl.String,
            "title": pl.String,
            "year_min": pl.Int16,
            "year_max": pl.Int16,
        },
        orient="row",
    )


def _right(rows: list[tuple[str, str, str | None, int | None, int | None]]) -> pl.DataFrame:
    return pl.DataFrame(
        rows,
        schema={
            "imdb_id": pl.String,
            "title": pl.String,
            "original_title": pl.String,
            "year": pl.Int16,
            "imdb_votes": pl.Int64,
        },
        orient="row",
    )


def test_normalise() -> None:
    assert normalise("Amélie") == "amelie"
    assert normalise("The Matrix") == "matrix"
    assert normalise("Fast & Furious") == "fast and furious"
    assert normalise("Schindler's List") == "schindlers list"
    assert normalise("Schindler’s List") == "schindlers list"
    assert normalise("Star Wars: Ep. VII -- Go!") == "star wars ep 7 go"
    assert normalise("  !!  ") is None
    assert normalise("") is None
    assert normalise(None) is None
    assert normalise("RRR (Hindi)") == "rrr"
    assert normalise("Death Wish (2018)") == "death wish"
    assert normalise("(500) Days of Summer") == "500 days of summer"
    assert normalise("(Untitled)") == "untitled"
    assert normalise("Blade II") == normalise("Blade 2") == "blade 2"
    assert normalise("John Wick: Chapter Two") == "john wick chapter 2"
    assert normalise("Twelve Monkeys") == "twelve monkeys"  # only two to ten
    assert normalise("I, Robot") == "i robot"  # a lone I stays a word


def test_exact_via_original_title() -> None:
    left = _left([("a", "Amélie", 2001, 2001)])
    right = _right([("tt1", "Other", "Amélie", 2001, 5)])
    assert match(left, right).rows() == [("a", "tt1", "exact", 100.0)]


def test_year_window_excludes() -> None:
    left = _left([("a", "Alien", 2000, 2001)])
    right = _right([("tt1", "Alien", None, 2003, 9), ("tt2", "Alien", None, None, 9)])
    assert match(left, right).height == 0


def test_exact_prefers_votes() -> None:
    left = _left([("a", "Dune", 2020, 2022)])
    right = _right([("tt1", "Dune", None, 2021, 10), ("tt2", "Dune", None, 2021, 500)])
    assert match(left, right)["imdb_id"].to_list() == ["tt2"]


def test_fuzzy_star_wars() -> None:
    left = _left([("a", "Star Wars Ep. VII: The Force Awakens", 2015, 2016)])
    right = _right([("tt1", "Star Wars: The Force Awakens", None, 2015, 9)])
    assert match(left, right).select("imdb_id", "method").rows() == [("tt1", "fuzzy")]


def test_fuzzy_match_and_cutoff() -> None:
    left = _left([("a", "Avatar The Way of Water", 2022, 2022), ("b", "Zzzz", 2022, 2022)])
    right = _right([("tt1", "Avatar: The Way of Waters", None, 2022, 9)])
    out = match(left, right)
    assert out.rows() == [("a", "tt1", "fuzzy", out["score"][0])]
    assert 90 <= out["score"][0] < 100
    assert match(left, right, min_score=99.9).height == 0


def test_output_schema() -> None:
    out = match(_left([("a", "Dune", 2021, 2021)]), _right([("tt1", "Dune", None, 2021, 1)]))
    assert out.columns == ["key", "imdb_id", "method", "score"]
    assert out.schema["score"] == pl.Float64


def test_apply_overrides() -> None:
    matches = pl.DataFrame(
        {
            "key": ["a", "b", "c"],
            "imdb_id": ["tt1", "tt2", "tt3"],
            "method": ["exact", "fuzzy", "exact"],
            "score": [100.0, 91.0, 100.0],
        }
    )
    overrides = pl.DataFrame(
        {"key": ["a", "b", "d"], "imdb_id": ["tt9", None, "tt8"]},
        schema={"key": pl.String, "imdb_id": pl.String},
    )
    out = apply_overrides(matches, overrides).sort("key")
    assert out.columns == matches.columns
    assert out.rows() == [
        ("a", "tt9", "override", None),
        ("c", "tt3", "exact", 100.0),
        ("d", "tt8", "override", None),
    ]


def test_fuzzy_rejects_different_numbers() -> None:
    a, b = "The Expendables 4", "The Expendables 2"
    assert fuzz.token_sort_ratio(normalise(a), normalise(b)) >= 90
    assert match(_left([("a", a, 2000, 2030)]), _right([("tt1", b, None, 2012, 9)])).height == 0
    # a number on one side only is fine; "1 2 3" and "123" carry the same digits
    jaws = match(
        _left([("j", "Jaws 4: The Revenge", 1987, 1987)]),
        _right([("tt2", "Jaws: The Revenge", None, 1987, 9)]),
    )
    assert jaws.height == 1
    pelham = match(
        _left([("p", "Pelham 1 2 3", 2009, 2009)]), _right([("tt3", "Pelham 123", None, 2009, 9)])
    )
    assert pelham.height == 1


def test_fuzzy_years_limits_fuzzy_only() -> None:
    left = _left([("a", "Devara", 1900, 2024), ("b", "Alien", 1900, 2021)])
    right = _right([("tt1", "Devar", None, 1966, 9), ("tt2", "Alien", None, 1979, 9)])
    assert match(left, right).height == 2
    assert match(left, right, fuzzy_years=2).rows() == [("b", "tt2", "exact", 100.0)]
