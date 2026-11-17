from pathlib import Path

from movies.scrape import kobis

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_top_reads_code_title_date_and_strips_commas():
    rows = kobis.parse_top((FIXTURES / "kobis_top.html").read_text())
    assert [r["kobis_code"] for r in rows] == ["20148851", "20124079", "20999999"]
    assert rows[0] == {
        "kobis_code": "20148851",
        "title_ko": "명량",
        "release_date": "2014-07-30",
        "admissions": 17_613_682,
        "rank": 1,
    }


def test_parse_total_sums_the_admissions_column():
    assert kobis.parse_total((FIXTURES / "kobis_all.html").read_text()) == 31_877_448


def test_parse_p8921_takes_the_first_sorted_imdb_id():
    payload = {
        "results": {
            "bindings": [
                {"kobis": {"value": "1"}, "imdb": {"value": "tt9"}},
                {"kobis": {"value": "1"}, "imdb": {"value": "tt2"}},
                {"kobis": {"value": "2"}, "imdb": {"value": "tt5"}},
            ]
        }
    }
    assert kobis.parse_p8921(payload) == {"1": "tt2", "2": "tt5"}


def test_assemble_adds_the_remainder_and_nulls_unmatched():
    top = kobis.parse_top((FIXTURES / "kobis_top.html").read_text())
    rows = kobis.assemble(2014, top, 40_000_000, {"20148851": "tt3"})
    assert [r["imdb_id"] for r in rows] == ["tt3", None, None, None]
    assert [r["match"] for r in rows] == ["p8921", None, None, None]
    assert rows[-1] == {
        "kobis_code": None,
        "title_ko": "other films",
        "imdb_id": None,
        "match": None,
        "year": 2014,
        "admissions": 40_000_000 - 31_877_448,
    }


def test_parse_labels_reads_year_or_none():
    payload = {
        "results": {
            "bindings": [
                {
                    "l": {"value": "베테랑"},
                    "imdb": {"value": "tt1"},
                    "date": {"value": "2015-08-05T00:00:00Z"},
                },
                {"l": {"value": "베테랑"}, "imdb": {"value": "tt2"}},
            ]
        }
    }
    assert kobis.parse_labels(payload) == {"베테랑": [("tt1", 2015), ("tt2", None)]}


def _row(code, title, date):
    return {"kobis_code": code, "title_ko": title, "release_date": date}


def test_pick_by_title_accepts_within_one_year_and_rejects_the_rest():
    rows = [_row("1", "가", "2015-08-05"), _row("2", "나", "2015-08-05"), _row("3", "다", None)]
    candidates = {"가": [("tt1", 2016)], "나": [("tt2", 1999)], "다": [("tt3", 2015)]}
    assert kobis.pick_by_title(rows, candidates) == ({"1": "tt1"}, 0)


def test_pick_by_title_rejects_ambiguous_candidates():
    rows = [_row("1", "가", "2015-08-05")]
    candidates = {"가": [("tt1", 2015), ("tt2", 2014), ("tt3", 1990)]}
    assert kobis.pick_by_title(rows, candidates) == ({}, 1)


def test_label_query_escapes_quotes_and_backslashes():
    query = kobis.label_query(['a"b', "c\\d"])
    assert '"a\\"b"@ko' in query and '"c\\\\d"@ko' in query


def test_assemble_marks_title_matches():
    top = kobis.parse_top((FIXTURES / "kobis_top.html").read_text())
    rows = kobis.assemble(2014, top, 40_000_000, {"20148851": "tt3"}, {"20124079": "tt4"})
    assert [(r["imdb_id"], r["match"]) for r in rows[:3]] == [
        ("tt3", "p8921"),
        ("tt4", "title"),
        (None, None),
    ]
