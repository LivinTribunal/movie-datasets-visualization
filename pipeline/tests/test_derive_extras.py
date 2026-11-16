import polars as pl

from movies.derive.extras import extras

STORY = pl.DataFrame(
    {
        "origin": ["numbers", "numbers", "tmdb", "tmdb", "tmdb"],
        "label": ["Original Screenplay", "Based on Play", "based on comic", "remake", "biography"],
        "category": ["original", "stage", "comic", "screen", "true_story"],
    }
)
STUDIOS = pl.DataFrame(
    {
        "company": ["Pixar", "Columbia Pictures", "Warner Bros. Pictures"],
        "studio": ["disney", "sony", "warner"],
    }
)
CPI = pl.DataFrame({"year": pl.Series([2000, 2025], dtype=pl.Int16), "cpi": [100.0, 200.0]})


def _film(imdb_id: str, **kw) -> dict:
    base = {
        "imdb_id": imdb_id,
        "year": 2000,
        "certification_us": None,
        "keywords": None,
        "companies": None,
        "cast": None,
        "writers": None,
        "overview": None,
        "qid": None,
        "numbers_key": None,
        "numbers_match": None,
    }
    return base | kw


def _metric(numbers_id: int, **kw) -> dict:
    base = {
        "numbers_id": numbers_id,
        "source": None,
        "mpaa_rating": None,
        "opening_weekend": None,
        "theaters_max": None,
        "legs": None,
        "video_sales": None,
    }
    return base | kw


FILM_SCHEMA = {
    "year": pl.Int16,
    "certification_us": pl.String,
    "keywords": pl.List(pl.String),
    "companies": pl.List(pl.String),
    "cast": pl.List(pl.String),
    "writers": pl.List(pl.String),
    "numbers_key": pl.String,
    "numbers_match": pl.String,
    "qid": pl.String,
    "overview": pl.String,
}
METRIC_SCHEMA = {
    "numbers_id": pl.Int32,
    "source": pl.String,
    "mpaa_rating": pl.String,
    "opening_weekend": pl.Float64,
    "theaters_max": pl.Int32,
    "legs": pl.Float64,
    "video_sales": pl.Float64,
}
WIKI = pl.DataFrame(
    {
        "imdb_id": ["tt1", "tt2"],
        "qid": ["Q1", "Q2"],
        "oscar_wins": pl.Series([2, None], dtype=pl.Int16),
        "oscar_noms": pl.Series([5, None], dtype=pl.Int16),
        "csfd_id": ["9", None],
        "filmaffinity_id": [None, None],
        "allocine_id": [None, None],
        "douban_id": [None, None],
    }
)


def _run(films: list[dict], metrics: list[dict] | None = None, wiki=None) -> pl.DataFrame:
    f = pl.DataFrame(films, schema={"imdb_id": pl.String, **FILM_SCHEMA})
    m = pl.DataFrame(metrics or [], schema=METRIC_SCHEMA)
    return extras(f, m, wiki, CPI, STORY, STUDIOS)


def _row(out: pl.DataFrame, imdb_id: str) -> dict:
    return out.filter(pl.col("imdb_id") == imdb_id).row(0, named=True)


def test_one_row_per_film_in_order():
    out = _run([_film("tt2"), _film("tt1")])
    assert out["imdb_id"].to_list() == ["tt2", "tt1"]


def test_story_source_numbers_over_tmdb_null_when_neither_first_mapped_keyword_wins():
    films = [
        _film("tt1", numbers_key="metrics:1", keywords=["based on comic"]),
        _film("tt2", keywords=["biography", "remake", "x"]),
        _film("tt3", keywords=["unmapped"]),
        _film("tt4", numbers_key="metrics:2"),
        _film("tt5", keywords=["biography", "based on comic"]),
    ]
    metrics = [_metric(1, source="Based on Play"), _metric(2, source="")]
    out = _run(films, metrics)
    assert _row(out, "tt1")["story_source"] == "stage"
    assert _row(out, "tt1")["story_source_src"] == "numbers"
    assert _row(out, "tt2")["story_source"] == "screen"  # `remake` is listed before `biography`
    assert _row(out, "tt2")["story_source_src"] == "tmdb"
    assert _row(out, "tt3")["story_source"] is None
    assert _row(out, "tt3")["story_source_src"] is None
    assert _row(out, "tt4")["story_source"] is None  # an empty Source says nothing
    assert _row(out, "tt5")["story_source"] == "comic"


def test_age_rating_prefers_tmdb_then_numbers_and_maps_not_rated():
    films = [
        _film("tt1", certification_us="PG", numbers_key="metrics:1"),
        _film("tt2", numbers_key="metrics:2"),
        _film("tt3", numbers_key="metrics:3"),
        _film("tt4", certification_us="X", numbers_key="metrics:4"),
        _film("tt5"),
    ]
    metrics = [
        _metric(1, mpaa_rating="R"),
        _metric(2, mpaa_rating="Not Rated"),
        _metric(3, mpaa_rating="Open"),
        _metric(4, mpaa_rating="PG-13"),
    ]
    out = _run(films, metrics)
    got = {r: _row(out, r)["age_rating"] for r in ("tt1", "tt2", "tt3", "tt4", "tt5")}
    assert got == {"tt1": "PG", "tt2": "NR", "tt3": None, "tt4": "PG-13", "tt5": None}


def test_studio_first_listed_company_independent_or_null():
    films = [
        _film("tt1", companies=["Nobody", "Columbia Pictures", "Pixar"]),
        _film("tt2", companies=["Nobody"]),
        _film("tt3", companies=None),
        _film("tt4", companies=["Pixar", "Columbia Pictures"]),
    ]
    out = _run(films)
    assert [_row(out, f"tt{i}")["studio"] for i in (1, 2, 3, 4)] == [
        "sony",
        "independent",
        None,
        "disney",
    ]


def test_cpi_scaling_and_metrics_only_for_metrics_keys():
    films = [
        _film("tt1", numbers_key="metrics:1"),
        _film("tt2", numbers_key="budgets:1"),
        _film("tt3"),
    ]
    metrics = [_metric(1, opening_weekend=1000.0, theaters_max=3000, legs=3.5, video_sales=500.0)]
    out = _run(films, metrics)
    r = _row(out, "tt1")
    assert r["opening_usd"] == 1000.0
    assert r["opening_usd2025"] == 2000.0
    assert r["video_usd2025"] == 1000.0
    assert (r["theaters"], r["legs"]) == (3000, 3.5)
    for other in ("tt2", "tt3"):
        row = _row(out, other)
        assert row["opening_usd"] is None
        assert row["theaters"] is None
        assert row["legs"] is None


def test_year_without_cpi_gives_null_2025_value():
    films = [_film("tt1", year=1950, numbers_key="metrics:1")]
    out = _run(films, [_metric(1, opening_weekend=10.0)])
    assert _row(out, "tt1")["opening_usd"] == 10.0
    assert _row(out, "tt1")["opening_usd2025"] is None


def test_numbers_fuzzy_needs_a_fuzzy_match_and_a_value():
    films = [
        _film("tt1", numbers_key="metrics:1", numbers_match="fuzzy"),
        _film("tt2", numbers_key="metrics:2", numbers_match="fuzzy"),
        _film("tt3", numbers_key="metrics:3", numbers_match="exact"),
        _film("tt4", numbers_key="budgets:4", numbers_match="fuzzy"),
        _film("tt5"),
    ]
    metrics = [
        _metric(1, theaters_max=10),
        _metric(2, source="Remake"),
        _metric(3, theaters_max=10),
    ]
    out = _run(films, metrics)
    assert out["numbers_fuzzy"].to_list() == [True, False, False, False, False]


def test_oscars_zero_with_qid_null_without_or_without_the_file():
    films = [
        _film("tt1"),
        _film("tt2"),
        _film("tt3", qid="Q3"),
        _film("tt4"),
    ]
    out = _run(films, wiki=WIKI)
    assert (_row(out, "tt1")["oscar_wins"], _row(out, "tt1")["oscar_noms"]) == (2, 5)
    assert (_row(out, "tt2")["oscar_wins"], _row(out, "tt2")["oscar_noms"]) == (0, 0)
    assert (_row(out, "tt3")["oscar_wins"], _row(out, "tt3")["oscar_noms"]) == (0, 0)
    assert _row(out, "tt4")["oscar_wins"] is None
    assert _row(out, "tt1")["csfd_id"] == "9"
    assert _row(out, "tt1")["qid"] == "Q1"
    missing = _run(films)
    assert missing["oscar_noms"].to_list() == [None] * 4
    assert _row(missing, "tt3")["qid"] == "Q3"


def test_detail_text_joins_lists_and_keeps_three_companies():
    films = [
        _film(
            "tt1",
            cast=["A", "B"],
            writers=["W"],
            companies=["a", "b", "c", "d"],
            overview="Plot.",
        )
    ]
    r = _row(_run(films), "tt1")
    assert (r["cast"], r["writers"], r["companies"], r["overview"]) == (
        "A, B",
        "W",
        "a, b, c",
        "Plot.",
    )
